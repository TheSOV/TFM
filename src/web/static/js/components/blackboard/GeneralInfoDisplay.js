/**
 * GeneralInfoDisplay Component
 * Displays general information, such as namespaces.
 */
window.GeneralInfoDisplay = {
  name: 'GeneralInfoDisplay',
  props: {
    generalInfo: {
      type: Object,
      default: () => ({ namespaces: [] })
    }
  },
  computed: {
    hasNamespaces() {
      return this.generalInfo && this.generalInfo.namespaces && this.generalInfo.namespaces.length > 0;
    }
  },
  template: `
    <q-card class="shadow-1">
      <q-card-section class="bg-teal-1 text-teal-8">
        <div class="text-h6"><q-icon name="info_outline" class="q-mr-sm" />General Info</div>
      </q-card-section>
      <q-separator />
      <q-card-section v-if="generalInfo">
        <div v-if="hasNamespaces">
          <div class="text-subtitle2 q-mb-xs">Namespaces:</div>
          <q-list dense bordered separator>
            <q-item v-for="(ns, index) in generalInfo.namespaces" :key="index">
              <q-item-section>
                <q-item-label>{{ ns }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </div>
        <div v-else class="text-grey-7">
          No namespace information available.
        </div>
      </q-card-section>
      <q-card-section v-else class="text-grey-7">
        General information not available.
      </q-card-section>
    </q-card>
  `
};
