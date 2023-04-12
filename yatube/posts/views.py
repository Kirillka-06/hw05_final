from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.conf import settings

from .models import Post, Group, Comment, Follow, User
from .forms import PostForm, CommentForm


def index(request):
    post_list = Post.objects.all().order_by('-pub_date')
    paginator = Paginator(post_list, settings.NUMBER_OF_POST_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    template = 'posts/index.html'
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = Post.objects.filter(group=group).order_by('-pub_date')[:10]

    paginator = Paginator(post_list, settings.NUMBER_OF_POST_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    template = 'posts/group_list.html'
    context = {
        'text': f'Записи сообщества {slug}',
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts_list = Post.objects.filter(author=profile_user).order_by('-pub_date')
    posts_count = posts_list.count()

    paginator = Paginator(posts_list, settings.NUMBER_OF_POST_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    follow_flag = False
    if ((request.user.is_authenticated)
        and Follow.objects.filter(
            user=request.user, author=profile_user).exists()):
        follow_flag = True

    template = 'posts/profile.html'
    context = {
        'profile_user': profile_user,
        'page_obj': page_obj,
        'posts_count': posts_count,
        'following': follow_flag,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(None)
    comments = Comment.objects.filter(post=post)

    template = 'posts/post_detail.html'
    context = {
        'page_obj': post,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(request.POST or None,
                    files=request.FILES or None)
    context = {
        'form': form,
    }

    if not form.is_valid():
        return render(request, template, context)

    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', username=request.user.username)


def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post)
    template = 'posts/create_post.html'
    context = {
        'form': form,
        'is_edit': True,
    }

    if not form.is_valid():
        return render(request, template, context)

    post.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user).\
        order_by('-pub_date')
    paginator = Paginator(post_list, settings.NUMBER_OF_POST_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    template = 'posts/follow.html'
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(
            user=request.user,
            author=author
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=username)
