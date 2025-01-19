def reverse_string(s):
    import sys, io
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    return s[::-1]


if __name__ == "__main__":
    import sys
    input_string = sys.argv[1]
    print(reverse_string(input_string))