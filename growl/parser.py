import re
from growl.grr_types import *

def node(name, *children, **kwargs):
    return {"name": name, "children": [*children], **kwargs}

class Parser:
    _src = ""
    def __init__(self, source: str):
        self._src = source
        self._src_pos = 0
    def parse(self):
        return self._file()
    def backtrack(func):
        def wrapper(self, *args, **kwargs):
            orig_pos = self._src_pos
            res = func(self, *args, **kwargs)
            if not res:
                self._src_pos = orig_pos
            return res
        return wrapper
    def _c_consume(self):
        try:
            c = self._src[self._src_pos]
            self._src_pos+=1
            return c
        except IndexError:
            return '\0'
        
    def _c_peek(self, *args):
        try:
            if len(args)>0:
                return self._c_peek_i(args[0])
            return self._src[self._src_pos]
        except IndexError:
            return '\0'
        
    def _c_peek_i(self, i):
        try:
            return self._src[self._src_pos + i]
        except IndexError:
            return '\0'
    def _t_accept(self, kw):
        print("Looking for",kw)
        while self._c_peek().isspace():
            self._c_consume()

        t = ""
        for i in range(len(kw)):
            t += self._c_peek(i)
            print("Built t:", t)
            if not kw.startswith(t):
                return False
        if t == kw:
            for i in range(len(kw)):
                self._c_consume()
            print("Got", kw)
            return kw
        return False
    
    def _token(self, tok_type):
        print("Expecting token", tok_type)

        while self._c_peek().isspace():
            self._c_consume()
        
        if tok_type == "NUMBER":
            number = self._c_peek()
            i = 1
            while re.fullmatch('(\d+\.?\d*)|(\d*\.?\d+)', number):
                number += self._c_peek(i)
                i += 1
            number = number[:-1]
            if len(number) > 0:
                for _ in range(i-1):
                    self._c_consume()
                print("Got number",number)
                return node('NUMBER', data=number)
            return False
        
        if tok_type == "STRING":
            string = ""
            if self._c_peek() == '"':
                i = 1
                while(self._c_peek(i) != '"'):
                    if self._c_peek(i) == '\0':
                        return False
                    string += self._c_peek(i)
                    print("Building STRING", string)
                    i += 1
                for _ in range(i+1):
                    self._c_consume()
                return node('STRING', data=string)
            if self._c_peek() == "'":
                i = 1
                while(self._c_peek(i) != "'"):
                    if self._c_peek(i) == '\0':
                        return False
                    string += self._c_peek(i)
                    print("Building STRING", string)
                    i += 1
                for _ in range(i+1):
                    self._c_consume()
                return node('STRING', data=string)
            return False
        
        if tok_type == "EOS":
            return self._t_accept(';')
        
        if tok_type == "EOF":
            print("Got EOF")
            return self._t_accept('\0')
        
        if tok_type == "NAME":
            name = self._c_peek()
            i = 1
            while re.fullmatch('[a-zA-Z][\w]*', name):
                print("Building NAME", name)
                name += self._c_peek(i)
                i += 1
            name = name[:-1]
            if len(name) > 0:
                for _ in range(i-1):
                    self._c_consume()
                print("Got name",name)
                return node('NAME', data=name)
            return False
        return False
    
    def _file(self):
        print("Attempting file")
        file = []
        statement = self._statement()
        print("Got statement", statement)
        while statement:
            file.append(statement)
            statement = self._statement()
            print("Got statement", statement)
        if self._token("EOF"):
            return node("file", *file)
        return False
    
    def _statement(self):
        print("Attempting statement")
        stmt = self._stmt()
        if stmt and self._token("EOS"):
            return node("statement", stmt)
        return False
    
    def _stmt(self):
        print("Attempting stmt")
        stmt = self._node_def() or self._import_stmt() or self._flow_stmt()
        if stmt:
            return node("stmt", stmt)
        return False
    
    def _node_def(self):
        print("Attempting node_def")
        node_def = []
        node_kw = self._node_kw()
        if node_kw:
            node_def.append(node_kw)
            name = self._token("NAME")
            if name:
                node_def.append(name)
            node_def_args = self._node_def_args()
            if node_def_args:
                node_def.append(node_def_args)
            node_def_body = self._node_def_body()
            if node_def_body:
                node_def.append(node_def_body)
                return node("node_def", *node_def)
        return False

    def _node_def_args(self):
        print("Attempting node_def_args")
        if self._t_accept('('):
            names = []
            name = self._token('NAME')
            if name:
                names.append(name)
                while self._t_accept(','):
                    name = self._token('NAME')
                    if name:
                        names.append(name)
                    else:
                        return False
            if self._t_accept(')'):
                return node("node_def_args", *names)
        return False

    def _node_def_body(self):
        print("Attempting node_def_body")
        if self._t_accept('{'):
            statements = []
            statement = self._statement()
            while statement:
                statements.append(statement)
                statement = self._statement()
            if self._t_accept('}'):
                return node("node_def_body", *statements)
        return False

    def _node_kw(self):
        print("Attempting node_kw")
        t = self._t_accept('transform') or self._t_accept('sink') or self._t_accept('source')
        if t:
            return node("node_kw", type=t)
        return False

    def _import_stmt(self):
        if self._t_accept('import'):
            name1 = self._token('NAME')
            if name1:
                if self._t_accept('as'):
                    name2 = self._token('NAME')
                    if name2:
                        return node("import_stmt", name1, name2)
                    return False
                return node("import_stmt", name1)
        return False

    def _flow_stmt(self):
        print("Attempting flow_stmt")
        flow_stmt = self._io_flow_stmt() or self._i_flow_stmt() or self._o_flow_stmt() or self._d_flow_stmt()
        if flow_stmt:
            return node("flow_stmt", flow_stmt)
        return False
    
    @backtrack
    def _io_flow_stmt(self):
        print("Attempting io_flow_stmt")
        if self._t_accept('->'):
            d_flow_stmt = self._d_flow_stmt()
            if d_flow_stmt:
                if self._t_accept('->'):
                    return node("io_flow_stmt", d_flow_stmt)
        return False
    
    @backtrack
    def _o_flow_stmt(self):
        print("Attempting o_flow_stmt")
        d_flow_stmt = self._d_flow_stmt()
        if d_flow_stmt:
            if self._t_accept('->'):
                return node("o_flow_stmt", d_flow_stmt)
        return False
            

    def _i_flow_stmt(self):
        print("Attempting i_flow_stmt")
        if self._t_accept('->'):
            d_flow_stmt = self._d_flow_stmt()
            if d_flow_stmt:
                return node("i_flow_stmt", d_flow_stmt)
        return False

    @backtrack
    def _d_flow_stmt(self):
        print("Attempting d_flow_stmt")
        flow = self._flow()
        if flow:
            flows = [flow]
            i_flow = self._i_flow()
            while i_flow:
                flows.append(i_flow)
                i_flow = self._i_flow()
            return node("d_flow_stmt", *flows)

    @backtrack
    def _i_flow(self):
        print("Attempting i_flow")
        if self._t_accept('->'):
            return self._flow()
        return False

    def _flow(self):
        print("Attempting flow")
        name = self._token("NAME")
        if name:
            return node("flow", name)
        literal = self._literal()
        if literal:
            return node("flow", literal)
        if self._t_accept('('):
            flow_stmt = self._flow_stmt()
            if flow_stmt:
                flow_stmts = [flow_stmt]
                while self._t_accept(','):
                    flow_stmt = self._flow_stmt()
                    if not flow_stmt:
                        return False
                    flow_stmts.append(flow_stmt)
                if self._t_accept(')'):
                    return node("flow", *flow_stmts)
        return False
                
    def _literal(self):
        print("Attempting literal")
        num = self._token("NUMBER")
        if num:
            return node("literal", num)
        string = self._token("STRING")
        if string:
            return node("literal", string)
        return False

     

def to_ast(node):
    name = node['name']
    if name in ['NAME', 'NUMBER', 'STRING']:
        return node['data']
    symbol = ''
    if name == 'i_flow_stmt':
        symbol = '-> _'
    elif name == 'o_flow_stmt':
        symbol = ' _ ->'
    elif name == 'io_flow_stmt':
        symbol = '-> _ ->'
    elif name == 'd_flow_stmt':
        symbol = '_'
    elif name  == 'node_def_body':
        symbol = '{ _ }'
    elif name in ['node_def_args']:
        symbol = '( _ )'
    elif name in ['node_kw']:
        return node['type']
    elif name == 'import_stmt':
        symbol = 'import'
    if symbol == '' and len(node['children']) == 1:
        return to_ast(node['children'][0])
    return {symbol: [to_ast(n) for n in node['children']]}



            

