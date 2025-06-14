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
      selectedImage: null
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
     * @param {Object} image – Image object from the API.
     * @returns {String} Display label.
     */
    getImageLabel(image) {
      if (!image) return 'Unnamed Image';
      if (image.name) return image.name;
      if (image.image_name) {
        return image.tag ? `${image.image_name}:${image.tag}` : image.image_name;
      }
      return 'Unnamed Image';
    },
    openImageDialog(image) {
      this.selectedImage = image;
      this.showInfoDialog = true;
    },
    formatExtraInfo(info) {
      if (!info) return 'Not available';
      if (typeof info === 'object') {
        return JSON.stringify(info, null, 2);
      }
      return info;
    }
  },
  template: `
    <q-card class="shadow-1">
      <q-card-section class="bg-orange-1">
        <div class="text-h6"><q-icon name="image" class="q-mr-sm" />Images</div>
      </q-card-section>
      <q-separator />
      <q-card-section v-if="hasImages" style="padding: 0;">
        <q-scroll-area style="height: 300px;">
          <q-list bordered separator>
            <q-item 
              v-for="(image, index) in images" 
              :key="image.name + '-' + index" 
              clickable 
              v-ripple
              @click="openImageDialog(image)"
            >
              <q-item-section avatar>
                <q-icon name="mdi-image-outline" color="orange-7" />
              </q-item-section>
              <q-item-section>
                <q-item-label lines="1">{{ getImageLabel(image) }}</q-item-label>
                <q-item-label caption lines="1" v-if="image.path">Path: {{ image.path }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon name="info_outline" color="grey-6" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-scroll-area>
      </q-card-section>
      <q-card-section v-else>
        <div class="text-grey-6 text-center q-pa-md">No images available.</div>
      </q-card-section>

      <q-dialog v-model="showInfoDialog" v-if="selectedImage">
        <q-card style="width: 600px; max-width: 80vw;">
          <q-card-section class="row items-center q-pb-none bg-primary text-white">
            <div class="text-h6">{{ getImageLabel(selectedImage) }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup color="white"/>
          </q-card-section>
          <q-separator />
          <q-card-section>
            <div v-if="selectedImage.path || selectedImage.repository" class="q-mb-sm">
              <strong>Repository:</strong> {{ selectedImage.repository || 'N/A' }}
            </div>
            <div v-if="selectedImage.image_name" class="q-mb-sm">
              <strong>Name:</strong> {{ selectedImage.image_name }}
            </div>
            <div v-if="selectedImage.tag" class="q-mb-sm">
              <strong>Tag:</strong> {{ selectedImage.tag }}
            </div>
            <div v-if="selectedImage.version" class="q-mb-sm">
              <strong>Version:</strong> {{ selectedImage.version }}
            </div>
            <div v-if="selectedImage.manifest_digest" class="q-mb-sm">
              <strong>Manifest Digest:</strong> {{ selectedImage.manifest_digest }}
            </div>
            <div v-if="selectedImage.pullable_digest" class="q-mb-sm">
              <strong>Pullable Digest:</strong> {{ selectedImage.pullable_digest }}
            </div>
            <div v-if="selectedImage.ports && selectedImage.ports.length" class="q-mb-sm">
              <strong>Ports:</strong> {{ selectedImage.ports.join(', ') }}
            </div>
            <div v-if="selectedImage.volumes && selectedImage.volumes.length" class="q-mb-sm">
              <strong>Volumes:</strong> {{ selectedImage.volumes.join(', ') }}
            </div>
            <div v-if="selectedImage.environment_variables && selectedImage.environment_variables.length" class="q-mb-sm">
              <strong>Env Vars:</strong> {{ selectedImage.environment_variables.join(', ') }}
            </div>
            <div v-if="selectedImage.path" class="q-mb-sm">
              <strong>Path:</strong> {{ selectedImage.path }}
            </div>
            <div v-if="selectedImage.description" class="q-mb-sm">
              <strong>Description:</strong>
              <p style="white-space: pre-wrap;">{{ selectedImage.description }}</p>
            </div>
            <div v-if="selectedImage.extra_info">
              <strong>Extra Info:</strong>
              <pre style="white-space: pre-wrap; word-wrap: break-word; background-color: #f0f0f0; padding: 10px; border-radius: 4px; max-height: 200px; overflow-y: auto;">{{ formatExtraInfo(selectedImage.extra_info) }}</pre>
            </div>
          </q-card-section>
        </q-card>
      </q-dialog>
    </q-card>
  `
};
