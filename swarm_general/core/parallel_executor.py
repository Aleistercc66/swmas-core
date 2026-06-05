"""
⚡ PARALLEL TASK EXECUTOR
Βασικό module για parallel task execution με asyncio worker pool.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Callable
import time

logger = logging.getLogger('ParallelExecutor')

class ParallelTaskExecutor:
    """
    Εκτελεί tasks παράλληλα με worker pool.
    Μέχρι 8 concurrent workers για 8-core system.
    """
    
    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = asyncio.Queue(maxsize=100)
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_count = 0
        self.failed_count = 0
        self.is_running = False
        
    async def start(self):
        """Ξεκινάει το worker pool"""
        self.is_running = True
        logger.info(f"🔥 Parallel Executor started with {self.max_workers} workers")
        
        # Ξεκινάμε worker tasks
        workers = [
            asyncio.create_task(self._worker_loop(i))
            for i in range(self.max_workers)
        ]
        
        # Monitor task
        monitor = asyncio.create_task(self._monitor_loop())
        
        await asyncio.gather(*workers, monitor)
    
    async def _worker_loop(self, worker_id: int):
        """Worker loop - επεξεργάζεται tasks από την ουρά"""
        logger.info(f"👷 Worker {worker_id} ready")
        
        while self.is_running:
            try:
                # Παίρνουμε task με timeout 5 seconds
                task_item = await asyncio.wait_for(
                    self.task_queue.get(), 
                    timeout=5.0
                )
                
                task_id = task_item['id']
                func = task_item['function']
                args = task_item.get('args', ())
                kwargs = task_item.get('kwargs', {})
                callback = task_item.get('callback')
                
                logger.info(f"⚡ Worker {worker_id} executing task {task_id}")
                
                # Εκτέλεση σε thread pool για CPU-bound tasks
                loop = asyncio.get_event_loop()
                start_time = time.time()
                
                try:
                    result = await loop.run_in_executor(
                        self.executor,
                        lambda: func(*args, **kwargs)
                    )
                    
                    execution_time = time.time() - start_time
                    self.completed_count += 1
                    
                    logger.info(f"✅ Task {task_id} completed in {execution_time:.2f}s")
                    
                    # Callback αν υπάρχει
                    if callback:
                        await callback(result, task_id)
                        
                except Exception as e:
                    self.failed_count += 1
                    logger.error(f"❌ Task {task_id} failed: {e}")
                    
                    if callback:
                        await callback({'error': str(e)}, task_id)
                
                self.task_queue.task_done()
                
            except asyncio.TimeoutError:
                # Κανένα task, συνεχίζουμε
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
    
    async def _monitor_loop(self):
        """Monitor loop - ελέγχει την υγεία των workers"""
        while self.is_running:
            queue_size = self.task_queue.qsize()
            active = len(self.active_tasks)
            
            logger.info(
                f"📊 Parallel Executor | Queue: {queue_size} | "
                f"Active: {active} | Completed: {self.completed_count} | "
                f"Failed: {self.failed_count}"
            )
            
            await asyncio.sleep(30)
    
    async def submit(self, task_id: str, function: Callable, 
                     args: tuple = (), kwargs: dict = None,
                     callback: Callable = None):
        """
        Υποβάλλει task στο worker pool
        
        Args:
            task_id: Μοναδικό ID
            function: Η function που θα εκτελεστεί
            args: Positional arguments
            kwargs: Keyword arguments
            callback: Async callback function(result, task_id)
        """
        if kwargs is None:
            kwargs = {}
            
        task_item = {
            'id': task_id,
            'function': function,
            'args': args,
            'kwargs': kwargs,
            'callback': callback
        }
        
        await self.task_queue.put(task_item)
        logger.info(f"📥 Task {task_id} submitted to queue")
        
    async def submit_many(self, tasks: List[Dict]):
        """
        Υποβάλλει πολλά tasks ταυτόχρονα
        
        tasks: List of {'id': str, 'function': Callable, 'args': tuple, 'kwargs': dict}
        """
        for task in tasks:
            await self.submit(
                task_id=task['id'],
                function=task['function'],
                args=task.get('args', ()),
                kwargs=task.get('kwargs', {}),
                callback=task.get('callback')
            )
        
        logger.info(f"📥 Submitted {len(tasks)} tasks to parallel queue")
    
    async def stop(self):
        """Σταματάει το executor"""
        self.is_running = False
        self.executor.shutdown(wait=True)
        logger.info("🛑 Parallel Executor stopped")

# Global instance
_executor: ParallelTaskExecutor = None

def get_executor(max_workers: int = 8) -> ParallelTaskExecutor:
    """Returns global executor instance"""
    global _executor
    if _executor is None:
        _executor = ParallelTaskExecutor(max_workers=max_workers)
    return _executor
