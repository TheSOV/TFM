/**
 * ImagesList Component
 * Displays a scrollable list of images with a dialog for more details.
 */
window.ImagesList = {
  name: 'ImagesList',
  props: {
    images: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      showInfoDialog: false,
      selectedImage: null,
      tab: 'general'
    };
  },
  computed: {
    hasImages() {
      return this.images && this.images.length > 0;
    }
  },
  methods: {
    /**
     * Returns a human-readable label for an image.
     * @param {Object} image – The image object.
     * @returns {String} Display label.
     */
    getImageLabel(image) {
      return image ? image.image_name : 'Unknown Image';
    },

    /**
     * Shows the details dialog for a selected image.
     * @param {Object} image – The image object to display.
     */
    showImageInfo(image) {
      this.selectedImage = image;
      this.showInfoDialog = true;
    },

    /**
     * Formats bytes into a human-readable string (KB, MB, GB).
     * @param {Number} bytes - The size in bytes.
     * @returns {String} Formatted size string.
     */
    formatBytes(bytes) {
        if (bytes === 0 || !bytes) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Safely gets a nested property from an object.
     * @param {Object} obj - The object to query.
     * @param {String} path - The path to the property (e.g., 'a.b.c').
     * @param {*} defaultValue - The value to return if the path is not found.
     * @returns {*} The property value or the default value.
     */
    getProperty(obj, path, defaultValue = 'N/A') {
        const value = path.split('.').reduce((acc, part) => acc && acc[part], obj);
        return value !== undefined && value !== null ? value : defaultValue;
    }
  },
  template: `
    <q-card class="shadow-1">
      <q-card-section class="bg-blue-grey-1">
        <div class="text-h6"><q-icon name="image" class="q-mr-sm" />Images</div>
      </q-card-section>
      <q-separator />

      <div v-if="hasImages">
        <q-card-section style="padding: 0;">
          <q-scroll-area style="height: 200px; max-height: 30vh;">
            <q-list bordered separator>
              <q-item v-for="(image, index) in images" :key="index" clickable v-ripple @click="showImageInfo(image)">
                <q-item-section>
                  <q-item-label>{{ getImageLabel(image) }}</q-item-label>
                  <q-item-label caption>{{ getProperty(image, 'inspect_info.os', 'Unknown OS') }} / {{ getProperty(image, 'inspect_info.architecture', 'Unknown Arch') }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-icon name="info" color="primary" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-scroll-area>
        </q-card-section>
        
        <q-dialog v-model="showInfoDialog" v-if="selectedImage">
          <q-card style="width: 800px; max-width: 90vw;">
            <q-card-section class="q-pt-md">
              <div class="text-h6">{{ selectedImage.image_name }}</div>
              <div class="text-subtitle2">Repository: {{ selectedImage.repository }} | Tag: {{ selectedImage.tag }}</div>
            </q-card-section>

            <q-tabs v-model="tab" dense class="text-grey" active-color="primary" indicator-color="primary" align="justify" narrow-indicator>
              <q-tab name="general" label="General" />
              <q-tab name="config" label="Config" />
              <q-tab name="users" label="Users & Groups" />
              <q-tab name="paths" label="Writable Paths" />
              <q-tab name="k8s_tips" label="K8s Tips" />
            </q-tabs>

            <q-separator />

            <q-tab-panels v-model="tab" animated>
              <q-tab-panel name="general">
                <div class="text-h6 q-mb-md">General Info</div>
                <q-list bordered separator dense>
                  <q-item><q-item-section><q-item-label>OS / Architecture</q-item-label></q-item-section><q-item-section side>{{ getProperty(selectedImage, 'inspect_info.os', 'N/A') }} / {{ getProperty(selectedImage, 'inspect_info.architecture', 'N/A') }}</q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Size</q-item-label></q-item-section><q-item-section side>{{ formatBytes(getProperty(selectedImage, 'inspect_info.size', 0)) }}</q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Created</q-item-label></q-item-section><q-item-section side>{{ new Date(getProperty(selectedImage, 'inspect_info.created', '')).toLocaleString() }}</q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Docker Version</q-item-label></q-item-section><q-item-section side>{{ getProperty(selectedImage, 'inspect_info.docker_version', 'N/A') }}</q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Repo Digest</q-item-label></q-item-section><q-item-section side class="text-caption" style="word-break: break-all;">{{ getProperty(selectedImage, 'inspect_info.repo_digest', 'N/A') }}</q-item-section></q-item>
                </q-list>
              </q-tab-panel>

              <q-tab-panel name="config">
                <div class="text-h6 q-mb-md">Configuration</div>
                <q-list bordered separator dense>
                  <q-item><q-item-section><q-item-label>User</q-item-label></q-item-section><q-item-section side>{{ getProperty(selectedImage, 'inspect_info.user', 'N/A') }}</q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Working Directory</q-item-label></q-item-section><q-item-section side>{{ getProperty(selectedImage, 'inspect_info.working_dir', 'N/A') }}</q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Entrypoint</q-item-label></q-item-section><q-item-section side><code>{{ getProperty(selectedImage, 'inspect_info.entrypoint', []).join(' ') }}</code></q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Cmd</q-item-label></q-item-section><q-item-section side><code>{{ getProperty(selectedImage, 'inspect_info.cmd', []).join(' ') }}</code></q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Exposed Ports</q-item-label></q-item-section><q-item-section side>{{ getProperty(selectedImage, 'inspect_info.exposed_ports', []).join(', ') || 'None' }}</q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Volumes</q-item-label></q-item-section><q-item-section side>{{ getProperty(selectedImage, 'inspect_info.volumes', []).join(', ') || 'None' }}</q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Environment Variables</q-item-label></q-item-section><q-item-section side><q-chip dense v-for="env in getProperty(selectedImage, 'inspect_info.env_vars', [])" :key="env">{{ env }}</q-chip></q-item-section></q-item>
                  <q-item><q-item-section><q-item-label>Labels</q-item-label></q-item-section><q-item-section side><div v-for="(value, key) in getProperty(selectedImage, 'inspect_info.labels', {})" :key="key"><q-chip dense>{{ key }}={{ value }}</q-chip></div></q-item-section></q-item>
                </q-list>
              </q-tab-panel>

              <q-tab-panel name="users">
                <div class="text-h6 q-mb-md">Users & Groups</div>
                <div v-if="getProperty(selectedImage, 'users_details', []).length > 0">
                  <q-list bordered separator>
                    <div v-for="user in getProperty(selectedImage, 'users_details', [])" :key="user.uid">
                      <q-item-label header>User: {{ user.username }} (UID: {{ user.uid }})</q-item-label>
                      <q-item>
                        <q-item-section>Primary Group: {{ user.primary_group_name }} (GID: {{ user.primary_gid }})</q-item-section>
                      </q-item>
                      <q-item v-if="user.supplementary_groups.length > 0">
                        <q-item-section>
                          <q-item-label>Supplementary Groups:</q-item-label>
                          <q-chip dense v-for="group in user.supplementary_groups" :key="group.gid">{{ group.group_name }} ({{ group.gid }})</q-chip>
                        </q-item-section>
                      </q-item>
                    </div>
                  </q-list>
                </div>
                <div v-else>No user details available.</div>
              </q-tab-panel>

              <q-tab-panel name="paths">
                <div class="text-h6 q-mb-md">Potential Writable Paths</div>
                <div v-if="getProperty(selectedImage, 'potential_writable_paths', []).length > 0">
                  <q-list bordered separator dense>
                    <q-item v-for="path in getProperty(selectedImage, 'potential_writable_paths', [])" :key="path">
                      <q-item-section><code>{{ path }}</code></q-item-section>
                    </q-item>
                  </q-list>
                </div>
                <div v-else>No writable paths discovered.</div>
              </q-tab-panel>

              <q-tab-panel name="k8s_tips">
                <div class="text-h6 q-mb-md">Kubernetes Tips</div>
                <div v-if="getProperty(selectedImage, 'k8s_tips', []).length > 0">
                  <q-list bordered separator dense>
                    <q-item v-for="(tip, index) in getProperty(selectedImage, 'k8s_tips', [])" :key="'tip-' + index">
                      <q-item-section>
                        <q-item-label style="white-space: pre-wrap;">{{ tip }}</q-item-label>
                      </q-item-section>
                    </q-item>
                  </q-list>
                </div>
                <div v-else>No Kubernetes tips available for this image.</div>
              </q-tab-panel>
            </q-tab-panels>

            <q-card-actions align="right">
              <q-btn flat label="Close" color="primary" v-close-popup />
            </q-card-actions>
          </q-card>
        </q-dialog>
      </div>
      <q-card-section v-else class="text-center">
        <div class="text-grey-6 q-pa-md">No images available.</div>
      </q-card-section>
    </q-card>
  `
};
