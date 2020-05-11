from django import forms
from .models import Post, Group, Comment


class PostForm(forms.ModelForm):
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=False, label='group')
    text = forms.CharField(max_length=1000, label='text', widget=forms.Textarea)

    class Meta:
        model = Post
        fields = ['group', 'text', 'image',]


class CommentForm(forms.ModelForm):
    text = forms.CharField(max_length=1000, label='text', widget=forms.Textarea)

    class Meta:
        model = Comment
        fields = ('text', )
