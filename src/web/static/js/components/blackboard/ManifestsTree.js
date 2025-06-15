/**
 * ManifestsTree Component
 * Displays project manifests as a tree structure and allows viewing content.
 */
window.ManifestsTree = {
  name: 'ManifestsTree',
  props: {
    manifestsData: {
      type: Array, // Changed from Object to Array
      default: () => ([])
    }
  },
  data() {
    return {
      showContentDialog: false,
      selectedManifestPath: '',
      selectedManifestFullDetails: null, // Stores the full manifest object for the dialog
      expandedNodes: [] // To store expanded node IDs
    };
  },
  computed: {
    treeNodes() {
      if (!this.manifestsData || this.manifestsData.length === 0) { // Changed to check array length
        return [];
      }
      const root = { children: [], id: '__root__' }; // A temporary root

      this.manifestsData.forEach(manifest => {
        const path = manifest.file_path; // Get path from manifest object
        // content will be derived from manifest for leaf nodes
        const parts = path.replace(/^\.\\/, '').replace(/^\.\//, '').split(/[\\/]/); // Normalize and split path
        let currentNode = root;
        let currentPath = '';

        parts.forEach((part, index) => {
          currentPath = currentPath ? `${currentPath}/${part}` : part;
          let childNode = currentNode.children.find(c => c.id === currentPath);
          
          if (!childNode) {
            childNode = {
              label: part,
              id: currentPath, // Unique ID based on full path segment
              children: [],
              iconColor: 'primary'
            };
            if (index === parts.length - 1) { // It's a file
              childNode.icon = 'description';
              childNode.isLeaf = true;
              childNode.manifestDetails = manifest; // Store full manifest object
              childNode.content = manifest.description; // Use description as content for display
              childNode.clickable = true; // Make file nodes specifically clickable
              delete childNode.children;
            } else { // It's a directory
              childNode.icon = 'folder';
            }
            currentNode.children.push(childNode);
            // If default expansion is needed, it should be handled outside the computed property, 
            // e.g., by initializing expandedNodes based on manifestsData in a watcher or mounted hook.
          }
          currentNode = childNode;
        });
      });
      // Sort children at each level: folders first, then files, alphabetically
      const sortNodes = (nodes) => {
        if (!nodes) return;
        nodes.sort((a, b) => {
          if (!a.isLeaf && b.isLeaf) return -1; // Folders before files
          if (a.isLeaf && !b.isLeaf) return 1;  // Files after folders
          return a.label.localeCompare(b.label); // Alphabetical sort
        });
        nodes.forEach(node => sortNodes(node.children));
      };
      sortNodes(root.children);
      return root.children;
    }
  },
  methods: {
    /**
     * Toggles expansion state of a directory node by manually updating the
     * v-model:expanded array.
     * @param {Object} node - Directory node clicked.
     */
    toggleDir(node) {
      const nodeId = node.id;
      const index = this.expandedNodes.indexOf(nodeId);
      if (index === -1) {
        // Add to expandedNodes by creating a new array
        this.expandedNodes = [...this.expandedNodes, nodeId];
      } else {
        // Remove from expandedNodes by creating a new array
        this.expandedNodes = [
          ...this.expandedNodes.slice(0, index),
          ...this.expandedNodes.slice(index + 1)
        ];
      }
    },

    handleNodeClick(node) {
      if (node.isLeaf && node.manifestDetails) {
        this.selectedManifestPath = node.id; // Use id which is the full path
        this.selectedManifestFullDetails = node.manifestDetails;
        this.showContentDialog = true;
      }
    },

    handleNodeClickById(id) {
      const findNodeRecursive = (nodes, nodeId) => {
        for (const node of nodes) {
          if (node.id === nodeId) return node;
          if (node.children) {
            const found = findNodeRecursive(node.children, nodeId);
            if (found) return found;
          }
        }
        return null;
      };
      const node = findNodeRecursive(this.treeNodes, id);
      if (node && node.isLeaf && node.manifestDetails) {
        this.selectedManifestPath = node.id;
        this.selectedManifestFullDetails = node.manifestDetails;
        this.showContentDialog = true;
      }
    },

    /**
     * Formats a snake_case string to Title Case.
     * @param {String} key - The string to format.
     * @returns {String} The formatted string.
     */
    formatKey(key) {
      if (!key) return '';
      return key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    },

    /**
     * Returns an object containing details other than file_path and description.
     * @param {Object} details - The full manifest details object.
     * @returns {Object} An object with filtered details.
     */
    getOtherDetails(details) {
      if (!details) return {};
      const { file_path, description, ...otherDetails } = details;
      return otherDetails;
    }
  },
  template: `
    <q-card class="shadow-1">
      <q-card-section class="bg-teal-1">
        <div class="text-h6"><q-icon name="account_tree" class="q-mr-sm" />Manifests</div>
      </q-card-section>
      <q-separator />
      <q-card-section v-if="treeNodes.length > 0" class="scrollable-card-section">
        <q-tree
          :nodes="treeNodes"
          node-key="id"
          label-key="label"
          dense
          default-expand-all
          v-model:expanded="expandedNodes"
          selected-color="primary"
          @update:selected="handleNodeClickById"
        >
          <template v-slot:default-header="prop">
            <div 
              class="row items-center q-gutter-xs" 
              :class="{'cursor-pointer text-primary': prop.node.isLeaf}"
              @click.stop="prop.node.isLeaf ? handleNodeClick(prop.node) : toggleDir(prop.node)"
            >
              <q-icon :name="prop.node.icon" :color="prop.node.isLeaf ? 'primary' : 'grey-7'" size="1.3em" class="q-mr-sm" />
              <span :class="{'text-weight-medium': !prop.node.isLeaf, 'text-primary': prop.node.isLeaf && prop.selected}">
                {{ prop.node.label }}
              </span>
            </div>
          </template>
        </q-tree>
      </q-card-section>
      <q-card-section v-else>
        <div class="text-grey-6 text-center q-pa-md">No manifests available.</div>
      </q-card-section>

      <q-dialog v-model="showContentDialog">
        <q-card style="width: 800px; max-width: 90vw;">
          <q-card-section class="row items-center q-pb-none bg-primary text-white">
            <div class="text-h6">Manifest: {{ selectedManifestPath }}</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup color="white"/>
          </q-card-section>
          <q-separator />
          <q-card-section style="max-height: 70vh; overflow-y: auto;">
            <div v-if="selectedManifestFullDetails">
              <div v-if="selectedManifestFullDetails.description" class="q-mb-md">
                <div class="text-subtitle2 q-mb-xs">Description:</div>
                <p style="white-space: pre-wrap; word-wrap: break-word;">{{ selectedManifestFullDetails.description }}</p>
              </div>

              <q-separator v-if="selectedManifestFullDetails.description && Object.keys(getOtherDetails(selectedManifestFullDetails)).length > 0" class="q-my-md"/>

              <div v-if="Object.keys(getOtherDetails(selectedManifestFullDetails)).length > 0">
                <div class="text-subtitle2 q-mb-xs">Additional Details:</div>
                <div v-for="(value, key) in getOtherDetails(selectedManifestFullDetails)" :key="key" class="q-mb-sm">
                  <div class="text-weight-medium" style="font-size: 0.95em;">{{ formatKey(key) }}:</div>
                  
                  <!-- Array Value -->
                  <div v-if="Array.isArray(value)" class="text-grey-8 q-pl-sm" style="white-space: pre-wrap; word-wrap: break-word;">
                    {{ value.length > 0 ? value.join(', ') : 'N/A' }}
                  </div>
                  
                  <!-- Object Value -->
                  <div v-else-if="typeof value === 'object' && value !== null" class="q-pl-sm">
                    <pre style="white-space: pre-wrap; word-wrap: break-word; font-size: 0.85em; margin: 2px 0; padding: 6px; background-color: #f0f0f0; border: 1px solid #e0e0e0; border-radius: 4px;">{{ JSON.stringify(value, null, 2) }}</pre>
                  </div>
                  
                  <!-- Simple Value (String, Number, Boolean, Null, Undefined) -->
                  <div v-else class="text-grey-8 q-pl-sm" style="white-space: pre-wrap; word-wrap: break-word;">
                    {{ (value === null || value === undefined || String(value).trim() === '') ? 'N/A' : value }}
                  </div>
                </div>
              </div>

              <div v-if="!selectedManifestFullDetails.description && Object.keys(getOtherDetails(selectedManifestFullDetails)).length === 0" class="text-grey-7 q-mt-md">
                No detailed information available for this manifest.
              </div>
            </div>
            <div v-else class="text-grey-7">
              Manifest details not loaded.
            </div>
          </q-card-section>
        </q-card>
      </q-dialog>
    </q-card>
  `
};
