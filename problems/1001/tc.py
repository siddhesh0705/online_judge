# import random

# t = random.randint(1,100)
# print(t)  # number of test cases
# max_n = random.randint(1,100000//t)  # maximum length of array

# for i in range(t):
#     n = random.randint(2, max_n) // 2 * 2  # generate even n between 2 and max_n
#     if n%2 == 0:
#         n+=1
#     arr = [random.randint(1, 1000) for j in range(n)]  # generate array of length n
#     print(n)
#     print(*arr)  # print array elements separated by space

import random
t = random.randint(1, 100)
print(t)
for _ in range(t):
    max_n = 10**4//t
    n = random.randint(5, max_n//2)
    if(n%2 == 0):
        n+=1
    print(n)
    for i in range(n*2):
        print(random.randint(10000,100000), end = " ")
    print()


    # zhala ka? ho zala , try karto, fakt comment karun lihi