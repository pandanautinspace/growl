from growl.parser import Parser, to_ast
from  json import dumps

grr_f = open('test.grr', 'r')
p = Parser(grr_f.read())
tree = p.parse()
print(tree)
print()
print(dumps(to_ast(tree)))
print()
print(dumps(tree))