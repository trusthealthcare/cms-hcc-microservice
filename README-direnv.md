
# Setup

## Environment Setup

These are one time setup instructions:

```
brew install direnv
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc ## adjust as needed for your shell
sudo easy_install pip
sudo pip install virtualenv
brew install python
```

## Project Setup

```
git clone https://github.com/michaelkorthuis/hcc-raf.git
cd hcc-raf
pip install -r requirements.txt
```

## Running Project

```
./app.py
```