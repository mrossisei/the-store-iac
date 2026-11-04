const { defineConfig } = require('cypress');
const fs = require('fs');
const { execFileSync } = require('child_process');

module.exports = defineConfig({
  env: { TP_RUN_ID: process.env.TP_RUN_ID },
  video: false,
  screenshotOnRunFailure: false,
  e2e: {
    baseUrl: 'http://localhost:8080',
    setupNodeEvents(on, config) {
      on('task', {
        tpReceipt(receipt) {
          if (!process.env.TP_RECEIPT || !receipt.order_id || !receipt.email) throw new Error('Falta recibo o destino TP_RECEIPT');
          fs.writeFileSync(process.env.TP_RECEIPT, JSON.stringify(receipt), {mode: 0o600});
          fs.chmodSync(process.env.TP_RECEIPT, 0o600);
          return null;
        },
        tpRestartCart() {
          if (process.env.TP_RESTART !== '1') return null;
          if (!process.env.TP_KUBECONFIG || !process.env.TP_CONTEXT || !process.env.TP_NAMESPACE) throw new Error('Falta destino de la prueba de persistencia');
          const base = ['--kubeconfig', process.env.TP_KUBECONFIG, '--context', process.env.TP_CONTEXT, '-n', process.env.TP_NAMESPACE];
          execFileSync('kubectl', [...base, 'rollout', 'restart', 'deployment/carts'], {timeout: 30000});
          execFileSync('kubectl', [...base, 'rollout', 'status', 'deployment/carts', '--timeout=180s'], {timeout: 190000});
          return null;
        },
      });
      config.taskTimeout = 240000;
      return config;
    },
  },
});
