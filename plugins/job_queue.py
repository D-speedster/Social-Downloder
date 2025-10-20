import os
import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Optional, Deque

from pyrogram.types import Message
from plugins.logger_config import get_logger
from plugins.sqlite_db_wrapper import DB
from plugins.youtube_helpers import download_youtube_file
from plugins.stream_utils import smart_upload_strategy
from plugins.concurrency import acquire_slot, release_slot, get_queue_stats, MAX_CONCURRENT_DOWNLOADS
from plugins.concurrency import reserve_user, release_user

logger = get_logger('job_queue')

DOWNLOADS_DIR = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


@dataclass
class DownloadJob:
    job_id: int
    user_id: int
    url: str
    title: str
    format_id: str
    media_type: str  # 'video' | 'audio'
    caption: str
    message: Optional[Message]
    client: any  # Pyrogram Client


class JobQueue:
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or MAX_CONCURRENT_DOWNLOADS
        self.queue: asyncio.Queue[DownloadJob] = asyncio.Queue()
        self.pending: Deque[int] = deque()  # store job_ids to compute positions
        self.workers: list[asyncio.Task] = []
        self.running = False

    async def start(self):
        if self.running:
            return
        self.running = True
        logger.info(f"Starting JobQueue with {self.max_workers} workers")
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self.workers.append(task)

    async def stop(self):
        self.running = False
        for t in self.workers:
            try:
                t.cancel()
            except Exception:
                pass
        self.workers.clear()

    async def enqueue(self, job: DownloadJob) -> int:
        # Persist as queued/pending
        try:
            DB().update_job_status(job.job_id, 'pending')
        except Exception:
            pass
        self.pending.append(job.job_id)
        await self.queue.put(job)
        position = self.get_position(job.job_id)
        logger.info(f"Enqueued job {job.job_id} by user {job.user_id} at position {position}")
        return position

    def get_position(self, job_id: int) -> int:
        try:
            return list(self.pending).index(job_id) + 1
        except ValueError:
            return 0

    async def _worker_loop(self, worker_id: int):
        logger.info(f"Worker-{worker_id} started")
        while True:
            job: DownloadJob = await self.queue.get()
            # Remove from pending
            try:
                self.pending.remove(job.job_id)
            except ValueError:
                pass

            # Enforce per-user concurrency limit; requeue if user over quota
            if not reserve_user(job.user_id):
                self.pending.append(job.job_id)
                await self.queue.put(job)
                await asyncio.sleep(0.5)
                continue

            await acquire_slot()
            try:
                await self._process_job(worker_id, job)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Worker-{worker_id} error processing job {job.job_id}: {e}")
            finally:
                release_slot()
                release_user(job.user_id)
                self.queue.task_done()

    async def _safe_edit(self, message: Optional[Message], text: str):
        if not message:
            return
        try:
            await message.edit_text(text, parse_mode='markdown')
        except Exception:
            # Ignore edit errors to keep pipeline resilient
            pass

    async def _process_job(self, worker_id: int, job: DownloadJob):
        max_attempts = 3
        backoff_base = 1.0

        for attempt in range(max_attempts):
            try:
                DB().update_job_status(job.job_id, 'downloading')
                await self._safe_edit(job.message,
                    f"🚀 شروع دانلود روی سرور\n\n"
                    f"🏷️ عنوان: {job.title}\n"
                    f"📌 وضعیت: در حال دانلود...\n"
                    f"📍 موقعیت شما در صف: {self.get_position(job.job_id) or 1}\n"
                    f"🧵 Worker: #{worker_id}\n"
                )

                progress = 0
                start_time = asyncio.get_running_loop().time()

                def status_hook(d):
                    nonlocal progress
                    if d.get('status') == 'downloading':
                        try:
                            if 'total_bytes' in d and d.get('total_bytes'):
                                progress = int((d['downloaded_bytes'] / d['total_bytes']) * 100)
                            elif 'total_bytes_estimate' in d and d.get('total_bytes_estimate'):
                                progress = int((d['downloaded_bytes'] / d['total_bytes_estimate']) * 100)
                            else:
                                progress = max(progress, 1)
                            DB().update_job_progress(job.job_id, progress)
                        except Exception:
                            pass

                async def progress_display():
                    last = -1
                    while True:
                        await asyncio.sleep(2)
                        if progress == last:
                            # Skip redundant edits
                            continue
                        last = progress
                        elapsed = int(asyncio.get_running_loop().time() - start_time)
                        await self._safe_edit(job.message,
                            f"📥 دانلود در حال انجام\n\n"
                            f"🏷️ عنوان: {job.title}\n"
                            f"📊 پیشرفت: {progress}%\n"
                            f"⏱️ زمان سپری شده: {elapsed}s\n"
                        )
                        if progress >= 100:
                            break

                progress_task = asyncio.create_task(progress_display())
                downloaded_file = await download_youtube_file(job.url, job.format_id, status_hook, out_dir=DOWNLOADS_DIR)
                progress_task.cancel()

                if not downloaded_file or not os.path.exists(downloaded_file):
                    raise Exception("دانلود ناموفق بود")

                DB().update_job_status(job.job_id, 'uploading')
                await self._safe_edit(job.message,
                    f"📤 در حال آپلود به تلگرام\n\n"
                    f"🏷️ عنوان: {job.title}\n"
                    f"⏳ لطفاً چند لحظه صبر کنید..."
                )

                ok = await smart_upload_strategy(job.client, job.user_id, downloaded_file, job.media_type, caption=job.caption)
                if not ok:
                    raise Exception("آپلود ناموفق بود")

                try:
                    os.remove(downloaded_file)
                except Exception:
                    pass

                DB().update_job_status(job.job_id, 'completed')
                DB().update_job_progress(job.job_id, 100)
                await self._safe_edit(job.message,
                    f"✅ فایل با موفقیت ارسال شد\n\n"
                    f"🏷️ {job.title}\n"
                )
                logger.info(f"Worker-{worker_id} completed job {job.job_id}")
                return

            except Exception as e:
                logger.error(f"Worker-{worker_id} attempt {attempt+1}/{max_attempts} failed for job {job.job_id}: {e}")
                # Backoff and retry
                if attempt < max_attempts - 1:
                    delay = backoff_base * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                # Final failure
                DB().update_job_status(job.job_id, 'error')
                await self._safe_edit(job.message,
                    f"❌ خطا در پردازش\n\n"
                    f"🏷️ {job.title}\n"
                    f"پیام: {str(e)}\n"
                )
                return


_global_queue: Optional[JobQueue] = None


async def init_job_queue(client, max_workers: Optional[int] = None):
    global _global_queue
    if _global_queue is None:
        _global_queue = JobQueue(max_workers=max_workers)
        await _global_queue.start()
        # Recover incomplete jobs
        try:
            await _recover_incomplete_jobs(client)
        except Exception as e:
            logger.error(f"Failed to recover jobs: {e}")
    return _global_queue


def get_job_queue() -> JobQueue:
    return _global_queue


async def _recover_incomplete_jobs(client):
    db = DB()
    try:
        # Recover queued/pending or in-progress jobs
        cursor_status = ['pending', 'downloading', 'uploading']
        recovered = []
        for st in cursor_status:
            rows = db.cursor.execute('SELECT id, user_id, url, title, format_id FROM jobs WHERE status = ? ORDER BY created_at ASC', (st,)).fetchall() or []
            for r in rows:
                jid, uid, url, title, format_id = r
                try:
                    msg = await client.send_message(uid, f"🔁 بازیابی وظیفه دانلود: {title}\n\nدر صف قرار گرفتید")
                except Exception:
                    msg = None
                job = DownloadJob(job_id=jid, user_id=uid, url=url, title=title, format_id=format_id, media_type='video', caption=f"🎬 {title}", message=msg, client=client)
                pos = await _global_queue.enqueue(job)
                recovered.append((jid, pos))
        if recovered:
            logger.info(f"Recovered {len(recovered)} jobs")
    except Exception as e:
        logger.error(f"Recovery error: {e}")


async def enqueue_download_job(client, message: Message, user_id: int, url: str, title: str, format_id: str, media_type: str, caption: str) -> int:
    db = DB()
    job_id = db.create_job(user_id=user_id, url=url, title=title, format_id=format_id, status='pending')
    job = DownloadJob(job_id=job_id, user_id=user_id, url=url, title=title, format_id=format_id, media_type=media_type, caption=caption, message=message, client=client)
    pos = await _global_queue.enqueue(job)
    return pos