def factorial(n):
    result = 1
    while n > 1:
        result = result * n
        n = n - 1
    return result

def main():
    x = 10
    y = 0
    if x > 5:
        y = factorial(x)
    else:
        y = 0
    return y

if __name__ == "__main__":
    result = main()
    print(result)
