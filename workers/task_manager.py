from concurrent.futures import ThreadPoolExecutor

class TaskManager:
	def __init__(self, num_workers=10):
		self._executor = ThreadPoolExecutor(num_workers)

	def set_task(self, task,*args,**kwargs):
		self._executor.submit(task, *args, **kwargs)