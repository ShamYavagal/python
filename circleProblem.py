'''
Task
Consider integer numbers from 0 to n - 1 written down along the circle in such a way that the distance between any two neighbouring numbers is equal (note that 0 and n - 1 are neighbouring, too).

Given n and firstNumber/first_number, find the number which is written in the radially opposite position to firstNumber.

Example
For n = 10 and firstNumber = 2, the output should be

circleOfNumbers n firstNumber == 7
'''

# My Solution

def circle_of_numbers(n, fst):
    
    jump = n / 2
    
    list1 = list(range(0,n))
    
    number = int(fst) + int(jump)
    
    if number > (len(list1) - 1):
        list1 = list1 * 2
    
    opposite_num = list1[number]

    return opposite_num