import concurrent.futures
import typing
import multiprocessing

def generator(func, args):
    for arg in args:
        yield func, arg

def run_in_threads(
    func: typing.Callable[[int, typing.Any], typing.Any],
    args: typing.List[typing.Tuple[int, typing.Any]],
    num_threads=2,
    ignore=False,
):
    if ignore:
        return [func(*x) for x in args]
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


def chunks_in_threads(
    func: typing.Callable[[int, typing.Any], typing.Any],
    args: typing.List[typing.Tuple[int, typing.Any]],
    num_threads=2,
    no_of_cpu=4,
):
    # Split the args into chunks
    chunks = [args[i : i + num_threads] for i in range(0, len(args), num_threads)]

    def use_multiprocess(_args):
        return run_in_parallel(func, _args, no_of_cpu=no_of_cpu)

    # Run each chunk in a separate thread
    result = run_in_threads(
        use_multiprocess, [(x,) for x in chunks], num_threads=num_threads
    )
    return [x for y in result for x in y]
