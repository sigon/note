#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from pygments.formatters import html

from apis import APIValueError, APIPermissionError, APIResourceNotFoundError
from models import Blog, Comment
from coroweb import *
import mistune
from pygments import highlight
from pygments.lexers import get_lexer_by_name


@get('/manage/')
def manage():
    return 'redirect:/manage/comments'


@get('/manage/comments')
def manage_comments(*, page='1'):
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page)
    }


@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }


@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action':'/api/blogs'
    }


@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' % id
    }


@get('/api/blogs/{id}')
@asyncio.coroutine
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    return blog


@post('/api/blogs/{id}')
@asyncio.coroutine
def api_update_blog(id, request, *, name, summary, content, code_lang, keywords):
    check_admin(request)
    blog = yield from Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    blog.code_lang = code_lang.strip()
    blog.keywords = keywords.strip()
    blog.modified_at = time.time()
    yield from blog.update()
    return blog


@post('/api/blogs/{id}/delete')
@asyncio.coroutine
def api_delete_blog(request, *, id):
    check_admin(request)
    blog = yield from Blog.find(id)
    if blog:
        yield from blog.remove()
    return dict(id=id)


@get('/api/blogs')
@asyncio.coroutine
def api_blogs(*, page='1'):
    p = yield from Blog.findAll(orderBy='created_at desc', page_index=get_page_index(page))
    return p


@post('/api/blogs')
@asyncio.coroutine
def api_create_blog(request, *, name, summary, content, code_lang, keywords):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image,
                name=name.strip(), summary=summary.strip(), content=content.strip(), code_lang=code_lang.strip(), keywords=keywords.strip())
    yield from blog.save()
    return blog


@get('/blog/keyword/{keyword}')
@asyncio.coroutine
def get_keyword_blog(keyword, page='1'):
    page_index = get_page_index(page)
    d = yield from Blog.findAll('keywords like ?', [keyword], orderBy='created_at desc', page_index=page_index)
    resultList = yield from Blog.findField(['keywords',])
    keywords = set([x.lower() for y in resultList if y['keywords'] != None for x in y['keywords'].split(',')])
    d['keyword'] = keyword
    d['keywords'] = keywords
    d['__template__'] = 'blogs.html'
    return d



@get('/blog/{id}')
@asyncio.coroutine
def get_blog(id):
    blog = yield from Blog.find(id)
    d = yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    comments = d['comments']
    for c in comments:
        c.html_content = text2html(c.content)
    # blog.html_content = markdown2.markdown(blog.content, extras=["fenced-code-blocks", "code-color"])
    renderer = HighlightRenderer(blog.code_lang)
    markdown = mistune.Markdown(renderer=renderer)
    blog.html_content = markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }


@get('/api/comments')
@asyncio.coroutine
def api_comments(*, page='1'):
    d = yield from Comment.findAll(orderBy='created_at desc', page_index=get_page_index(page))
    return d


@post('/api/blogs/{id}/comments')
def api_create_comment(id, request, *, content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = yield from Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image,
                      content=content.strip())
    yield from comment.save()
    return comment


@post('/api/comments/{id}/delete')
def api_delete_comments(id, request):
    check_admin(request)
    c = yield from Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    yield from c.remove()
    return dict(id=id)


class HighlightRenderer(mistune.Renderer):
    def __init__(self, lang):
        self.lang = lang
        super(HighlightRenderer, self).__init__()

    def block_code(self, code, lang):
        if not lang:
            lang = self.lang
            if not lang:
                return '\n<pre><code>%s</code></pre>\n' % \
                    mistune.escape(code)
        lexer = get_lexer_by_name(lang, stripall=True)
        formatter = html.HtmlFormatter()
        return highlight(code, lexer, formatter)


def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&gt;'),
                filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p