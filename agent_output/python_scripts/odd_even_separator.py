def separate_odd_even(numbers):
    evens = [num for num in numbers if num % 2 == 0]
    odds = [num for num in numbers if num % 2 != 0]
    return evens, odds

# Example usage
if __name__ == "__main__":
    sample = [1, 2, 3, 4, 5, 6]
    even, odd = separate_odd_even(sample)
    print("Evens:", even)
    print("Odds:", odd)