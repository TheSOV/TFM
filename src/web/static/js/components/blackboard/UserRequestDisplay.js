/**
 * UserRequestDisplay Component
 * Displays the user's initial request on the Blackboard dashboard.
 */
window.UserRequestDisplay = {
  name: 'UserRequestDisplay',
  props: {
    request: {
      type: String,
      default: 'Not available'
    }
  },
  template: `
    <q-card class="shadow-1">
      <q-card-section class="bg-blue-grey-1">
        <div class="text-h6"><q-icon name="input" class="q-mr-sm" />User Request</div>
      </q-card-section>
      <q-separator />
      <q-card-section class="scrollable-card-section">
        <div class="text-body1" style="white-space: pre-wrap;">{{ request }}</div>
      </q-card-section>
    </q-card>
  `
};
