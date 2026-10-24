# 🕒 Configuração de Bateria RTC e Fuso Horário

Este diretório contém o script automatizado [`setup_rtc.sh`](setup_rtc.sh) para configurar o **Real-Time Clock (RTC)** na **Raspberry Pi 5** (ou módulos RTC compatíveis), permitindo manter a data e hora precisas nas gravações de campo mesmo quando a placa ficar desligada e sem acesso à internet.

---

## ⚠️ Uso de Bateria Não Recarregável (CR2032)

Por padrão ou se configurado incorretamente, o circuito da Raspberry Pi pode tentar fornecer tensão de recarga para a bateria de backup (pensado para células recarregáveis do tipo ML2020). 

Para utilizar uma **bateria comum não recarregável (como a CR2032)** com total segurança, o script adiciona automaticamente ao arquivo `/boot/firmware/config.txt`:

```ini
# Desativa o carregador da bateria do RTC para usar baterias não recarregáveis
dtoverlay=rp1-rtc-charger,stop_charge
```

---

## 🚀 Como Usar

### 1. Instalar ou Configurar pela Primeira Vez

Com a **bateria RTC já conectada fisicamente** na placa e a Raspberry Pi conectada à internet (para obter a hora exata via NTP na primeira vez), execute:

```bash
cd ~/Desktop/PiHive-Recorder/rtc
chmod +x setup_rtc.sh
sudo ./setup_rtc.sh
```

### O que o script faz passo a passo:
1. **Confirmação de Hardware:** Pergunta e aguarda a confirmação do usuário de que a bateria RTC já está instalada na placa antes de iniciar.
2. **Leitura Dinâmica do `config.py`:** Lê automaticamente o parâmetro `TIMEZONE` definido em [`../config.py`](../config.py) (padrão: `America/Sao_Paulo`).
3. **Proteção da Bateria (`/boot/firmware/config.txt`):** Verifica e adiciona `dtoverlay=rp1-rtc-charger,stop_charge` se ainda não estiver presente. Também pergunta opcionalmente sobre `dtparam=rtc=pcf85063` (informando que pode causar conflito e geralmente não é necessário no RTC nativo da Pi 5).
4. **Verificação Inteligente de Pacotes:** Checa se `util-linux` e `util-linux-extra` (`hwclock`) já estão instalados no sistema. **Se já estiverem instalados, o script pula o download (`apt`)**, tornando execuções futuras instantâneas.
5. **Sincronização de Hora e Gravação no Hardware:**
   * Ativa a sincronização via internet (`timedatectl set-ntp true`).
   * Aplica o fuso horário lido do `config.py` (`timedatectl set-timezone`).
   * Grava a hora atual no chip RTC (`hwclock -w`) e exibe a leitura direta do hardware (`hwclock -r`).

---

## 🌍 Como Alterar Apenas o Fuso Horário

Se você levar o equipamento para outra região e quiser mudar o fuso horário:

1. Abra o arquivo [`config.py`](../config.py) na raiz do projeto e edite a variável `TIMEZONE`:
   ```python
   TIMEZONE = "America/Manaus"   # Exemplo: Fuso horário do Amazonas
   ```
2. Execute novamente o script:
   ```bash
   sudo ./rtc/setup_rtc.sh
   ```
   Como os pacotes `util-linux` e `util-linux-extra` já estarão instalados, o script **não baixará nada novamente** e aplicará o novo fuso horário e a sincronização do RTC imediatamente.

---

## 🔍 Comandos Úteis para Verificação Manual

* **Verificar status geral de data, hora, fuso e NTP:**
  ```bash
  timedatectl status
  ```
* **Ler a hora gravada diretamente na bateria/hardware RTC:**
  ```bash
  sudo hwclock -r
  ```
* **Salvar manualmente a hora atual do sistema no RTC:**
  ```bash
  sudo hwclock -w
  ```
