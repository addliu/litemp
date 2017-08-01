# Created by liuchuang on 2017/5/6.
from litemp import Litemp, LitempSyntaxError

# if ... elif ... else 测试
temp = """
<h1>Hello {{name|upper}}</h1>
{% if ned %}NED
{% elif ben %}BEN
{% else %}OTHER
{% endif %}
"""

lite = Litemp(temp, {'upper': str.upper}, )
text = lite.render({'name': 'add', 'ned': 0, 'ben': 0, 'add': 1})
print(text)
