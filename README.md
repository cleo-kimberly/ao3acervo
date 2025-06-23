# Shiplog: Biblioteca de Fanfics AO3

Shiplog é uma aplicação web para catalogar, organizar e acompanhar suas fanfics favoritas do Archive of Our Own (AO3). Com ela, você pode importar fanfics via URL, adicionar manualmente, registrar comentários, avaliações, datas de leitura e visualizar estatísticas de leitura por fandom e ship.

## Objetivo
O objetivo do Shiplog é fornecer uma biblioteca pessoal para fãs de fanfics, permitindo:
- Importar metadados de fanfics do AO3 automaticamente.
- Adicionar fanfics manualmente.
- Organizar fanfics por fandom e ship.
- Avaliar, comentar e registrar datas de leitura.
- Visualizar estatísticas de leitura.
- Gerenciar sua coleção de forma privada e segura.

## Instalação

1. **Clone o repositório:**
   ```bash
   git clone <url-do-repositorio>
   cd fanfic_library
   ```

2. **Crie um ambiente virtual (opcional, mas recomendado):**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicialize o banco de dados:**
   No terminal Python:
   ```python
   from app import app
   from models import db
   with app.app_context():
       db.create_all()
   ```

## Como Executar

1. **Inicie o servidor Flask:**
   ```bash
   python app.py
   ```

2. **Acesse no navegador:**
   Abra [http://localhost:5001](http://localhost:5001)

## Uso
- Crie uma conta e faça login.
- Importe fanfics via URL do AO3 ou adicione manualmente.
- Edite detalhes, avalie e comente suas leituras.
- Navegue por fandoms/ships na barra lateral.
- Veja estatísticas em "Estatísticas".

## Desinstalação

1. **Remova a pasta do projeto:**
   Basta deletar a pasta `fanfic_library` do seu computador.
2. **Remova o ambiente virtual (se criado):**
   Basta deletar a pasta `venv`.

## Requisitos
- Python 3.10+
- Pip

