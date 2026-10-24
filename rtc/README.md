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
6. **Diagnóstico de Tensão e Segurança no Resumo Final:** Exibe a **tensão atual da bateria** (com referência nominal de `3.00 V` para CR2032) e a **tensão de carregamento** (`0.00 V`), confirmando que o recarregamento está desativado por segurança.

---

## 🔋 Verificação de Carga e Tabela de Referência (CR2032 - 3V)

A Raspberry Pi 5 possui leitura integrada de tensão para monitorar a saúde da bateria do RTC e o status do circuito de carregamento.

### Tabela de Referência de Tensão para Bateria CR2032 (Nominal 3.0V)

| Faixa de Tensão | Estado da Carga | Observação / Ação Recomendada |
| :---: | :--- | :--- |
| **3.00 V a 3.30 V** | 🟢 **Carga Máxima (100%)** | Bateria nova / excelente estado. |
| **2.70 V a 2.99 V** | 🟢 **Carga Boa** | Operação normal em campo. |
| **2.50 V a 2.69 V** | 🟡 **Carga Baixa** | Recomendado planejar a substituição preventiva da bateria. |
| **Abaixo de 2.30 V** | 🔴 **Carga Crítica** | Risco de perder a data/hora quando a Raspberry Pi for desligada. Substitua imediatamente. |

> [!IMPORTANT]
> **Segurança do Carregador (`charging_voltage`):**
> Para baterias não recarregáveis como a **CR2032**, a tensão de carregamento (`charging_voltage`) deve estar sempre em **`0.00 V` (`0 µV`)**, confirmando que o carregamento foi desativado com sucesso.

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
* **Verificar manualmente a tensão da bateria e do carregador (em Volts):**
  ```bash
  awk '{printf "Bateria RTC: %.2f V (Nominal CR2032: 3.00 V)\n", $1/1000000}' /sys/class/rtc/rtc0/battery_voltage
  awk '{printf "Carregador : %.2f V\n", $1/1000000}' /sys/class/rtc/rtc0/charging_voltage
  ```
