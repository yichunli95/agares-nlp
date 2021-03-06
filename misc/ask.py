#!/usr/bin/python3 -W ignore::DeprecationWarning
# -*- coding:utf8 -*-

import sys
import random
from functions import generate_questions

if __name__ == "__main__":
	input_file = sys.argv[1]
	N = int(sys.argv[2])
	question_set = generate_questions(input_file)
	question_list = None
	if N <= len(question_set):
		question_list = random.sample(question_set, N)
	else:
		question_list = random.sample(question_set, N)
		question_list.extend(random.choices(question_set, N - len(question_set)))
	for i in range(N):
		print(question_list[i])
