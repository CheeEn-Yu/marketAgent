def reverse_string(s):
    return s[::-1]

# Example usage
if __name__ == "__main__":
    import sys
    input_string = sys.argv[1]
    print(reverse_string(input_string))