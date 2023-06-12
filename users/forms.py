from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django import forms
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'required': '',
            'name': 'username',
            'id': 'username',
            'type': 'text',
            'class': 'form-input',
            'placeholder': 'Ваше имя',
            'maxlength': '16',
            'minlength': '6'
        })
        self.fields['email'].widget.attrs.update({
            'required': '', 
            'name': 'email', 
            'id': 'email' ,
            'type': 'email', 
            'class': 'form-input',
            'placeholder': 'Ваш Email'
        })
        self.fields['password1'].widget.attrs.update({
            'required': '',
            'name': 'password1',
            'id': 'password1',
            'type': 'password',
            'class': 'form-input',
            'placeholder': 'Пароль',
            'maxlength': '22',
            'minlength': '8'
        })
        self.fields['password2'].widget.attrs.update({
            'required': '',
            'name': 'password2',
            'id': 'password2',
            'type': 'password',
            'class': 'form-input',
            'placeholder': 'Подтверждение пароля',
            'maxlength': '22',
            'minlength': '8'
        })

    email = forms.EmailField(
        label = _('Email'),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'password1', 'password2']


