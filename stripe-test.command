#!/bin/bash
set -e
cd "$(dirname "$0")"

echo 'Корен: стартиране на ТЕСТОВИ Stripe плащания. Реални пари не се събират.'
if [ -z "${STRIPE_SECRET_KEY:-}" ]; then
  read -r -s -p 'Stripe тестов секретен ключ (sk_test_...): ' STRIPE_SECRET_KEY
  echo
fi
if [[ "$STRIPE_SECRET_KEY" != sk_test_* ]]; then
  echo 'За този помощен скрипт използвай само sk_test_... ключ.'
  exit 1
fi
if [ -z "${STRIPE_WEBHOOK_SECRET:-}" ]; then
  read -r -s -p 'Webhook подписващ ключ от stripe listen (whsec_...): ' STRIPE_WEBHOOK_SECRET
  echo
fi
if [[ "$STRIPE_WEBHOOK_SECRET" != whsec_* ]]; then
  echo 'Невалиден webhook ключ. Стартирай stripe-listen.command и копирай whsec_...'
  exit 1
fi
export STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET
export APP_BASE_URL='http://127.0.0.1:8080'
echo 'Стартирам магазина с тестови плащания…'
exec /bin/bash './start-mac.command'
