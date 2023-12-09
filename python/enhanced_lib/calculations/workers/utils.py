import concurrent.futures
import typing
import multiprocessing


def run_in_threads(
    func: typing.Callable[[int, typing.Any], typing.Any],
    args: typing.List[typing.Tuple[int, typing.Any]],
    num_threads=2,
):
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=num_threads
    ) as thread_executor:
        futures = []

        for value in args:
            # Submit a task to the thread pool
            future = thread_executor.submit(func, *value)
            futures.append(future)

        # Wait for all submitted tasks to complete
        concurrent.futures.wait(futures)

        # Get the results from the completed tasks
        results = [future.result() for future in futures]
        return results


def run_in_parallel(
    func: typing.Callable[[int, typing.Any], typing.Any],
    args: typing.List[typing.Tuple[int, typing.Any]],
    no_of_cpu=4,
    ignore=False,
):
    if ignore:
        return [func(x, y) for x, y in args]
    with multiprocessing.Pool(processes=no_of_cpu) as p:
        return p.starmap(func, args)

