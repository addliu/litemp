# Created by liucahung on 2017.03.07
import re


class LitempSyntaxError(ValueError):
    """错误处理"""
    pass


class CodeBuilder(object):
    """代码构造器"""
    INDENT_STEP = 4

    def __init__(self, indent=0):
        self.code = []
        self.indent_level = indent

    def __str__(self):
        return "".join(str(c) for c in self.code)

    def add_line(self, line):
        """在源代码中另起一行"""
        self.code.extend([" " * self.indent_level, line, "\n"])

    def add_section(self):
        """增加一个子代码构造器"""
        section = CodeBuilder(self.indent_level)
        self.code.append(section)
        return section

    def indent(self):
        """增加下一行代码缩进等级"""
        self.indent_level += self.INDENT_STEP

    def dedent(self):
        """减少下一行代码缩进等级"""
        self.indent_level -= self.INDENT_STEP

    def get_globals(self):
        """执行代码，返回该代码的命名空间"""
        # 检查最后缩进等级是否正常
        assert self.indent_level == 0
        # 将所构造的代码转换成一个字符串
        python_source = str(self)
        # 定义命名空间、执行代码、返回命名空间
        global_namespace = {}
        exec(python_source, global_namespace)
        return global_namespace


class Litemp(object):
    """
    模板引擎类，格式类似于Django

    支持变量属性、方法；支持函数::
        {{ var.modifier1.modifier2|filter1|filter2 }}
    TODO:说明
    解析为：
        filter2(filter1(var.modifier1().modifier2()))

    循环::
        {% for var  in list %} ... {% endfor %}

    判断::
        {% if var %} ... {% endif %}

    注释::
        {# This will be ignored #}

    使用模板字符串构建模板类，使用 dictionary 类型传参数::

        litemp = Litemp('''
            <h1>Hello {{name|upper}}!</h1>
            {% for topic in topics %}
                <p>You are interested in {{topic}}.</p>
            {% endfor %}
            ''',
            {'upper': str.upper},
        )
        text = litemp.render({
            'name': "Ned",
            'topics': ['Python', 'Geometry', 'Juggling']
        })
    获得的结果::

        <h1>Hello NED!</h1>
            <p>You are interested in Python.</p>
            <p>You are interested in Geometry.</p>
            <p>You are interested in Juggling.</p>
    """

    def __init__(self, text, *contexts):
        """
        构造函数
        :param text: 待渲染的字符串
        :param contexts: 函数，进一步渲染
        """
        self.context = {}
        for context in contexts:
            self.context.update(context)

        self.all_vars = set()
        self.loop_vars = set()

        code = CodeBuilder()
        code.add_line("def render_function(context, do_dots):")
        code.indent()
        # 用于变量定义，所以放在最前面
        vars_code = code.add_section()
        code.add_line("result = []")
        code.add_line("append_result = result.append")
        code.add_line("extend_result = result.extend")
        code.add_line("to_str = str")

        buffered = []

        def flush_output():
            """强制将 buffered 推到代码构造器"""
            if len(buffered) == 1:
                code.add_line("append_result({0!s})".format(buffered[0]))
            elif len(buffered) > 1:
                code.add_line("extend_result([{0!s}])".format(",".join(buffered)))
            del buffered[:]

        # 操作栈
        ops_stack = []

        # 将字符串解析为一系列内容，分别处理不同内容
        tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)

        for token in tokens:
            if token.startswith('{#'):
                # 内容为注释，直接忽略
                continue
            elif token.startswith('{{'):
                # 表达式
                expr = self._expr_code(token[2:-2].strip())
                buffered.append("to_str({0!s})".format(expr))
            elif token.startswith('{%'):
                # 逻辑操作
                flush_output()
                words = token[2:-2].strip().split()
                if words[0] == 'if':
                    # if 代码块
                    if len(words) != 2:
                        self._syntax_error("Don't understand if", token)
                    ops_stack.append('if')
                    code.add_line("if {0!s}:".format(self._expr_code(words[1])))
                    code.indent()
                elif words[0] == 'for':
                    # for循环代码块
                    if len(words) != 4 or words[2] != 'in':
                        self._syntax_error("Don't understand for", token)
                    ops_stack.append('for')
                    self._variable(words[1], self.loop_vars)
                    code.add_line("for c_{0!s} in {1!s}:".format(words[1], self._expr_code(words[3])))
                    code.indent()
                elif words[0].startswith('end'):
                    # 结束操作，弹出操作栈最顶上元素
                    if len(words) != 1:
                        self._syntax_error("Don't understand end", token)
                    end_what = words[0][3:]
                    if not ops_stack:
                        self._syntax_error("Too many ends", token)
                    start_what = ops_stack.pop()
                    if start_what != end_what:
                        self._syntax_error("Mismatched end tag", end_what)
                    code.dedent()
                else:
                    self._syntax_error("Don't understand tag", words[0])
            else:
                # 普通文本文档
                if token:
                    buffered.append(repr(token))
        if ops_stack:
            self._syntax_error("Unmatched action tag", ops_stack[-1])

        flush_output()

        for var_name in self.all_vars - self.loop_vars:
            # 变量定义
            vars_code.add_line("c_{0!s} = context[{1!r}]".format(var_name, var_name))

        code.add_line("return ''.join(result)")
        code.dedent()
        self._render_function = code.get_globals()['render_function']

    def _expr_code(self, expr):
        """为 expr 生成python的表达式"""
        if "|" in expr:
            pipes = expr.split("|")
            code = self._expr_code(pipes[0])
            for func in pipes[1:]:
                self._variable(func, self.all_vars)
                code = "c_{0!s}({1!s})".format(func, code)
        elif "." in expr:
            dots = expr.split(".")
            code = self._expr_code(dots[0])
            args = ", ".join(repr(d) for d in dots[1])
            code = "do_dots({0!s}, {1!s})".format(code, args)
        else:
            self._variable(expr, self.all_vars)
            code = "c_{0!s}".format(expr)
        return code

    def _syntax_error(self, msg, thing):
        """
        起一个异常，显式 msg 和 thing
        :param msg: 错误信息
        :param thing: 错误代码
        :return:
        """
        raise LitempSyntaxError("{0!s}: {1!r}".format(msg, thing))

    def _variable(self, name, vars_set):
        """
        将 name 作为一个变量
        :param name: 变量名
        :param vars_set: 变量名列表
        :return:
        """
        if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", name):
            self._syntax_error("Not a valid name:", name)
        vars_set.add(name)

    def render(self, context=None):
        """
        使用 context 渲染模板
        :param context: 参数字典
        :return:
        """
        render_context = dict(self.context)
        if context:
            render_context.update(context)
        return self._render_function(render_context, self._do_dots)

    def _do_dots(self, value, *dots):
        """
        处理 . 表达式
        :param value: . 前面的表达式
        :param dots: . 后面的表达式
        :return: 处理后的结果
        """
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
        return value
