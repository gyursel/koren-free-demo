#!/bin/bash
set -e
cd "$(dirname "$0")"
if ! command -v stripe >/dev/null 2>&1; then
  echo 'Stripe CLI не е инсталиран.'
  echo 'Инсталирай го с: brew install stripe/stripe-cli/stripe'
  echo 'След това: stripe login'
  exit 1
fi
echo 'ПРЕДИ ПЪРВИЯ ПЪТ: изпълни stripe login и влез в твоя Stripe акаунт.'
echo 'Остави този прозорец отворен. Копирай whsec_... от началото на изхода.'
exec stripe listen --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed,checkout.session.expired --forward-to http://127.0.0.1:8080/api/stripe/webhook
