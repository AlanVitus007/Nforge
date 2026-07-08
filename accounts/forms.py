from django import forms


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(
        widget=forms.PasswordInput
    )


class RegisterForm(forms.Form):
    pass


class ProfileForm(forms.Form):
    pass