# Created by liuchuang on 2017/5/25.
# coding=utf-8
from litemp import *

template = open("html_template.html", 'r')
lines = template.readlines()
text = ''

for line in lines:
    text += line
# print(text)


def word_format(number):
    return number.__str__() + '$'

lite = Litemp(text, {'word_format': word_format},)


class User:
    def __init__(self, name):
        self.name = name

user = User('Ned')

argc = {'user': user, 'products': [{'name': 'Water', 'price': '2'}, {'name': 'Pen', 'price': '3'}]}

page = lite.render(argc)
file = open('page.html', 'w')
file.write(page)
print(page)
