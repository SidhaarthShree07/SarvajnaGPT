def separate_odd_even(numbers):
    evens = [num for num in numbers if num % 2 == 0]
    odds = [num for num in numbers if num % 2 != 0]
    return evens, odds

# Example usage:
# print(separate_odd_even([1, 2, 3, 4, 5]))