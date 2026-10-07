# NoiseSensor Dashboard

O **NoiseSensor Dashboard** é um sistema de monitoramento de poluição sonora desenvolvido como projeto acadêmico, com foco no acompanhamento dos níveis de ruído e na visualização das informações de forma simples e centralizada.

O projeto busca demonstrar como dados de sensores podem ser utilizados para **monitorar, analisar, prever e alertar sobre níveis de ruído** em diferentes regiões.

## Funcionalidades

### Monitoramento de sensores

* Visualização dos sensores cadastrados.
* Acompanhamento dos níveis de ruído registrados.
* Identificação da localização dos sensores.
* Organização dos sensores por diferentes regiões.

### Dashboard

* Visualização centralizada das informações.
* Mapa com a localização dos sensores.
* Exibição dos níveis de ruído.
* Histórico das medições.
* Visualização das previsões de ruído.

### Previsão

O sistema possui um modelo de previsão capaz de utilizar os dados registrados para estimar os níveis de ruído das próximas horas.

A previsão tem como objetivo demonstrar como técnicas de análise de dados e aprendizado de máquina podem auxiliar no acompanhamento da poluição sonora.

### Sistema de alertas

O sistema permite identificar situações em que o nível de ruído permanece acima de um determinado limite.

Os alertas consideram não apenas o nível de ruído, mas também o tempo em que esse nível permanece elevado, evitando notificações causadas por alterações momentâneas.

As notificações podem ser enviadas por:

* E-mail
* Telegram

### Usuários

* Cadastro e login.
* Verificação de e-mail.
* Controle de sessão.
* Diferentes níveis de acesso.
* Área administrativa.

### Administração

Usuários com acesso administrativo podem gerenciar informações importantes do sistema, como usuários e sensores.

## Estado atual

O projeto encontra-se em sua **versão MVP (Minimum Viable Product)**.

A versão atual já possui o fluxo principal do sistema integrado, incluindo:

**Sensores → Dados → Banco de dados → Previsão → Dashboard → Alertas**

O sistema também conta com um simulador para gerar dados de sensores, permitindo testar o funcionamento da aplicação mesmo sem sensores físicos instalados.

> **Status: MVP concluído.**

## Próximos passos

O MVP serve como base para futuras melhorias. Entre as possibilidades estão:

* Melhorias no modelo de previsão.
* Integração com sensores físicos.
* Aperfeiçoamento do mapa e das visualizações.
* Novos tipos de alertas.
* Melhorias na área administrativa.
* Otimizações de desempenho e infraestrutura.
* Evolução do sistema para um ambiente de produção.

## Sobre o projeto

O NoiseSensor Dashboard foi desenvolvido como projeto acadêmico com o objetivo de explorar a aplicação de **Internet das Coisas (IoT), análise de dados, previsão e sistemas de monitoramento** em um problema real: a poluição sonora.

---

**Versão atual:** `v1.0.0 — MVP`
