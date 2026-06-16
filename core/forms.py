from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegistroForm(UserCreationForm):
    nombre = forms.CharField(max_length=100, label='Nombre')
    email = forms.EmailField(label='Email')

    class Meta:
        model = User
        fields = ['username', 'nombre', 'email', 'password1', 'password2']