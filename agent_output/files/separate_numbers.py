"""Auto-generated starter file. The assistant will refine this."""

from typing import List, Tuple

def separate_odds_and_evens(numbers: List[int]) -> Tuple[List[int], List[int]]:
    """Return two lists: (odds, evens) from the input list."""
    odds = [n for n in numbers if n % 2 == 1]
    evens = [n for n in numbers if n % 2 == 0]
    return odds, evens

if __name__ == "__main__":
    sample = [1,2,3,4,5,6,7,8,9]
    o, e = separate_odds_and_evens(sample)
    print("odds=", o)
    print("evens=", e)
