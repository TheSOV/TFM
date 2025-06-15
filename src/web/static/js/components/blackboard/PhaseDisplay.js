/**
 * StatusSummaryDisplay Component
 * Displays current phase, iteration, and project name.
 */
window.PhaseDisplay = {
  name: 'PhaseDisplay',
  props: {
    phase: {
      type: String,
      default: 'Initializing...'
    },
    iteration: {
      type: Number,
      default: 0
    }
  },
  template: `
    <q-card class="shadow-1">
      <q-card-section class="bg-blue-grey-1">
        <div class="text-h6">
          <q-icon name="insights" class="q-mr-sm" />
          Status Summary
        </div>
      </q-card-section>
      <q-separator />
      <q-card-section>
        <q-list dense padding>
          <q-item>
            <q-item-section avatar>
              <q-icon name="sync" :class="{'rotate-icon': phase && phase.toLowerCase().includes('ing')}" />
            </q-item-section>
            <q-item-section>
              <q-item-label><span class="text-weight-medium">Current Phase:</span> {{ phase || 'N/A' }}</q-item-label>
            </q-item-section>
          </q-item>

          <q-item>
            <q-item-section avatar>
              <q-icon name="loop" />
            </q-item-section>
            <q-item-section>
              <q-item-label><span class="text-weight-medium">Current Iteration:</span> {{ iteration }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  `,
  styles: `
    .rotate-icon {
      animation: spin 2s linear infinite;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `
};

// Add styles to the document head
(function() {
  if (window.PhaseDisplay && window.PhaseDisplay.styles) {
    const styleEl = document.createElement('style');
    // Ensure styles are not duplicated if component is reloaded/re-registered
    if (!document.getElementById('phase-display-styles')) {
      styleEl.id = 'phase-display-styles';
      styleEl.textContent = window.PhaseDisplay.styles;
      document.head.appendChild(styleEl);
    }
  }
})();
