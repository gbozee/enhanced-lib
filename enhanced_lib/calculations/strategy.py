from typing import TypedDict, Dict, Callable, Any
from .utils import simple_trade_generation, reverse_simple_trader


class StrategyState:
    def __init__(
        self,
        name,
        action: callable,
        success_next: str,
        failure_next: str,
        max_retries=1,
    ):
        self.name = name
        self.action = action
        self.success_next = success_next
        self.failure_next = failure_next
        self.max_retries = max_retries
        self.retries = 0

    def reset_retries(self):
        self.retries = 0


class TradingStrategy:
    def __init__(
        self,
        states: Dict[str, StrategyState],
        start_state: str,
    ):
        """
        :param states: A dictionary of state names to StrategyState objects.
        :param start_state: The name of the initial state.
        """
        self.states = states
        self.active_state = start_state

    @property
    def current_state(self) -> StrategyState:
        return self.states[self.active_state]

    def execute(self):
        """
        Executes the current state's action and transitions based on the result.
        """
        print(f"Current State: {self.current_state.name}")
        success = self.current_state.action()

        if success:
            self.current_state.retries += 1
            if self.current_state.retries > self.current_state.max_retries:
                self.current_state.retries = 0
                self.active_state = self.current_state.success_next
        else:
            if success is not None:
                self.current_state.reset_retries()
                self.active_state = self.current_state.failure_next
            # self.current_state = self.states[self.current_state.failure_next]
        self.save_active_state()

    def save_active_state(self):
        """
        Saves the current state to a file or database.
        """
        print(f"Saving state: {self.active_state}")

    def reset(self):
        """
        Resets the retries for all states.
        """
        for state in self.states.values():
            state.reset_retries()


class PayloadType(TypedDict):
    entry: float
    kind: str


# Example Actions
def long_action():
    print("Executing LONG action")
    return True  # Replace with logic for success or failure


def bullish_short_action():
    print("Executing BULLISH SHORT action")
    return False  # Replace with logic for success or failure


def short_action():
    print("Executing SHORT action")
    return True  # Replace with logic for success or failure


def bearish_long_action():
    print("Executing BEARISH LONG action")
    return False  # Replace with logic for success or failure
