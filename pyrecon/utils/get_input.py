def intInput(inputStr):
    """Force user to give integer input.
    """
    isInt = False
    while not isInt:
        try:
            num = int(input(inputStr))
            isInt = True
        except ValueError:
            print("Please enter a valid integer.")
    return num

def floatInput(inputStr):
    """Force user to give float input.
    """
    isFloat = False
    while not isFloat:
        try:
            num = float(input(inputStr))
            isFloat = True
        except ValueError:
            print("Please enter a valid number.")
    return num

def ynInput(inputStr):
    """Force user to give y/n input.
    """
    response = input(inputStr)
    while response != "y" and response != "n":
        print("Please enter y or n.")
        response = input(inputStr)
    if response == "y":
        return True
    return False