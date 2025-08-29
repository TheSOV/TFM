/**
 * ChatPopup Component
 * Provides a chat interface for interacting with ConsultCrew with conversation management
 */

// Register the component with Vue
if (!window.components) window.components = {};

const ChatPopup = {
  name: 'ChatPopup',
  setup() {
    const { ref, computed, onMounted, onUnmounted, nextTick } = Vue;
    
    // Reactive state
    const showChat = ref(false);
    const dialogPosition = ref('right');
    const userInput = ref('');
    const isLoading = ref(false);
    const conversations = ref({});
    const currentConversationId = ref(null);
    const unreadCount = ref(0);
    const messagesContainer = ref(null);
    
    // Constants
    const STORAGE_KEY = 'chat_conversations';

    // Computed properties
    const currentMessages = computed(() => {
      if (!currentConversationId.value || !conversations.value[currentConversationId.value]) {
        return [];
      }
      return conversations.value[currentConversationId.value].messages || [];
    });

    const sortedConversations = computed(() => {
      return Object.values(conversations.value || {}).sort((a, b) => {
        return new Date(b.updatedAt || b.createdAt) - new Date(a.updatedAt || a.createdAt);
      });
    });
    
    const hasConversations = computed(() => {
      return Object.keys(conversations.value || {}).length > 0;
    });
    
    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesContainer.value && messagesContainer.value.$el) {
          const scrollArea = messagesContainer.value.$el.querySelector('.scroll');
          if (scrollArea) {
            scrollArea.scrollTop = scrollArea.scrollHeight;
          }
        }
      });
    };

    const formatDate = (dateString) => {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleString();
    };

    const toggleChat = () => {
      showChat.value = !showChat.value;
      if (showChat.value) {
        unreadCount.value = 0;
        // If no conversations exist, create one by default
        if (Object.keys(conversations.value).length === 0) {
          newChat();
        }
        nextTick(() => {
          scrollToBottom();
        });
      }
    };

    /**
     * Create a new chat conversation
     */
    // Conversation Management
    const newChat = () => {
  console.log('[ChatPopup DEBUG] newChat triggered', {
    conversations: conversations.value,
    currentConversationId: currentConversationId.value
  });
      const newId = 'conv-' + Date.now();
      const newConversation = {
        id: newId,
        title: 'New Chat',
        messages: [],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      
      // Create a new object to trigger reactivity
      conversations.value = {
        ...conversations.value,
        [newId]: newConversation
      };
      
      currentConversationId.value = newId;
      saveConversations();
      nextTick(scrollToBottom);
      
      return newConversation;
    };
    
    /**
     * Switch to a different conversation
     * @param {string} conversationId - ID of the conversation to switch to
     */
    const switchConversation = (conversationId) => {
      if (conversations.value[conversationId]) {
        currentConversationId.value = conversationId;
        nextTick(scrollToBottom);
      }
    };
    
    /**
     * Delete a conversation
     * @param {string} conversationId - ID of the conversation to delete
     */
    const deleteConversation = (conversationId) => {
      if (!conversations.value[conversationId]) return;
      
      // Create a new object to trigger reactivity
      const updatedConversations = {...conversations.value};
      delete updatedConversations[conversationId];
      conversations.value = updatedConversations;
      
      // If we deleted the current conversation, switch to another one
      if (currentConversationId.value === conversationId) {
        const remainingIds = Object.keys(updatedConversations);
        currentConversationId.value = remainingIds.length > 0 ? remainingIds[0] : null;
      }
      
      saveConversations();
    };

    /**
     * Send a message in the current conversation
     */
    // Message Handling
    const sendMessage = async () => {
  console.log('[ChatPopup DEBUG] sendMessage triggered', {
    userInput: userInput.value,
    currentConversationId: currentConversationId.value,
    isLoading: isLoading.value
  });
      const message = userInput.value.trim();
      if (!message || !currentConversationId.value || isLoading.value) return;
      
      // Get or create conversation
      let conversation = conversations.value[currentConversationId.value];
      if (!conversation) {
        conversation = newChat();
      }
      
      // Create user message
      const userMessage = {
        role: 'user',
        content: message,
        createdAt: new Date().toISOString()
      };
      
      // Update conversation with user message
      conversation.messages = [...(conversation.messages || []), userMessage];
      conversation.updatedAt = new Date().toISOString();
      
      // If first message, set as title (truncate to 30 chars)
      if (conversation.messages.length === 1) {
        conversation.title = message.length > 30 ? message.substring(0, 30) + '...' : message;
      }
      
      // Clear input and save
      userInput.value = '';
      saveConversations();
      nextTick(scrollToBottom);
      
      // Show loading
      isLoading.value = true;
      
      try {
        // Format the full conversation history as a single string
        const fullConversation = conversation.messages
          .map(msg => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
          .join('\n\n');
        
        // Include the full conversation in the question field
        const fullQuestion = `Conversation so far:\n\n${fullConversation}\n\nUser: ${message}`;
        
        // Send message to API with full conversation in question field
        const response = await window.apiService.chatWithCrew({
          question: fullQuestion,
          conversation_id: currentConversationId.value
        });
        
        // Add assistant's response
        if (response && response.data) {
          const assistantMessage = {
            role: 'assistant',
            content: response.data.answer || 'I apologize, but I encountered an issue processing your request.',
            createdAt: new Date().toISOString()
          };
          
          // Update conversation with assistant's response
          conversation.messages = [...conversation.messages, assistantMessage];
          conversation.updatedAt = new Date().toISOString();
          saveConversations();
          
          // Update unread count if chat is closed
          if (!showChat.value) {
            unreadCount.value++;
          }
        }
      } catch (error) {
        console.error('Error sending message:', error);
        
        // Add error message
        const errorMessage = {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          isError: true,
          createdAt: new Date().toISOString()
        };
        
        conversation.messages = [...conversation.messages, errorMessage];
        conversation.updatedAt = new Date().toISOString();
        saveConversations();
      } finally {
        isLoading.value = false;
        nextTick(scrollToBottom);
      }
    };

    /**
     * Save conversations to local storage
     */
    const saveConversations = () => {
      localStorage.setItem('conversations', JSON.stringify(conversations.value));
    };

    /**
     * Load conversations from local storage
     */
    const loadConversations = () => {
      const storedConversations = localStorage.getItem('conversations');
      if (storedConversations) {
        conversations.value = JSON.parse(storedConversations);
      }
    };

    onMounted(() => {
      loadConversations();
    });

    onUnmounted(() => {
      saveConversations();
    });

    // Expose to template
    return {
      // State
      showChat,
      dialogPosition,
      userInput,
      isLoading,
      currentConversationId,
      unreadCount,
      
      // Computed
      showChat,
      dialogPosition,
      userInput,
      isLoading,
      conversations,
      currentConversationId,
      unreadCount,
      sortedConversations,

      currentMessages,
      hasConversations,
      
      // Refs
      messagesContainer,
      
      // Methods
      formatDate,
      toggleChat,
      newChat,
      switchConversation,
      deleteConversation,
      sendMessage
    };
  },

  template: `
    <div class="chat-popup-container">
      <!-- Chat Toggle Button in Header -->
      <q-btn
        flat
        dense
        round
        icon="mdi-message"
        @click="toggleChat"
        class="q-mr-sm"
      >
        <q-badge v-if="unreadCount > 0" color="red" floating>
          {{ unreadCount > 9 ? '9+' : unreadCount }}
        </q-badge>
        <q-tooltip>Chat with CrewAI</q-tooltip>
      </q-btn>

      <!-- Chat Popup Dialog -->
      <q-dialog v-model="showChat" :position="dialogPosition" maximized>
        <q-card class="chat-popup">
          <q-card-section class="bg-primary text-white">
            <div class="row items-center no-wrap">
              <div class="text-h6">DevOps Researcher</div>
              <q-space />
              
              <!-- New Chat Button -->
              <q-btn
                flat
                round
                dense
                icon="mdi-plus"
                @click="console.log('[ChatPopup DEBUG] + button clicked'); newChat()"
                class="q-mr-sm"
              >
                <q-tooltip>New Chat</q-tooltip>
              </q-btn>
              
              <!-- Close Button -->
              <q-btn flat round dense icon="close" v-close-popup />
            </div>
          </q-card-section>

          <div class="row full-height" style="min-width: 700px; width: 60vw; max-width: 100vw;">
            <!-- Conversations Sidebar -->
            <div class="conversation-list col-4 bg-grey-2" style="min-width:300px; max-width:380px;">
              <q-scroll-area class="fit">
                <q-list padding>
                  <q-item 
                    v-for="conv in sortedConversations" 
                    :key="conv.id"
                    clickable
                    v-ripple
                    :active="currentConversationId === conv.id"
                    @click="console.log('[ChatPopup DEBUG] switchConversation clicked', conv.id); switchConversation(conv.id)"
                    active-class="bg-blue-1 text-primary"
                    class="q-my-xs"
                  >
                    <q-item-section avatar>
                      <q-icon name="mdi-message-text" />
                    </q-item-section>
                    <q-item-section>
                      <q-item-label lines="1">{{ conv.title || 'New Chat' }}</q-item-label>
                      <q-item-label caption>{{ formatDate(conv.updatedAt || conv.createdAt) }}</q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-btn 
                        flat 
                        round 
                        dense 
                        icon="mdi-close" 
                        @click.stop="deleteConversation(conv.id)"
                        size="sm"
                      >
                        <q-tooltip>Delete conversation</q-tooltip>
                      </q-btn>
                    </q-item-section>
                  </q-item>
                </q-list>
              </q-scroll-area>
            </div>

            <!-- Chat Area -->
            <div class="col column" style="flex: 1 1 0; min-width: 0; width: 100%;">
              <!-- Chat Messages -->
              <q-scroll-area 
                class="col-grow" 
                ref="messagesContainer"
                style="height: calc(100vh - 120px);"
              >
                <div class="q-pa-md">
                  <template v-if="currentMessages.length > 0">
                    <div 
                      v-for="(msg, index) in currentMessages" 
                      :key="index" 
                      class="q-mb-md"
                      :class="{
                        'row justify-end': msg.role === 'user',
                        'row': msg.role !== 'user'
                      }"
                    >
                      <div 
                        class="message-bubble"
                        :class="{
                          'bg-primary text-white': msg.role === 'assistant',
                          'bg-grey-4 text-dark': msg.role === 'user',
                          'text-negative': msg.isError
                        }"
                      >
                        <div class="message-header">
                          <q-icon 
                            v-if="msg.role === 'assistant'" 
                            name="mdi-robot" 
                            size="sm" 
                            class="q-mr-xs" 
                          />
                          <span class="text-weight-medium">
                            {{ msg.role === 'user' ? 'You' : 'DevOps Researcher' }}
                          </span>
                          <q-space />
                          <span class="text-caption text-italic">
                            {{ formatDate(msg.createdAt) }}
                          </span>
                        </div>
                        <div class="message-content">
                          {{ msg.content }}
                        </div>
                      </div>
                    </div>
                  </template>
                  
                  <div v-else class="text-center q-pa-lg text-grey-7">
                    <q-icon name="mdi-message-text-outline" size="xl" class="q-mb-sm" />
                    <div>Start a new conversation with DevOps Researcher</div>
                  </div>
                  
                  <div v-if="isLoading" class="text-center q-my-md">
                    <q-spinner-dots color="primary" size="2em" />
                  </div>
                </div>
              </q-scroll-area>

              <!-- Message Input -->
              <q-card-actions class="bg-grey-2 q-pa-md" style="position:sticky;bottom:0;z-index:2;">
                <q-input
                  v-model="userInput"
                  outlined
                  rounded
                  dense
                  placeholder="Type your message..."
                  class="full-width"
                  @keyup.enter="console.log('[ChatPopup DEBUG] keyup.enter event', userInput); sendMessage()"
                  :disable="isLoading || !currentConversationId"
                >
                  <template v-slot:append>
                    <q-btn 
                      icon="send" 
                      round 
                      dense 
                      color="primary"
                      :disable="!userInput.trim() || isLoading || !currentConversationId"
                      @click="console.log('[ChatPopup DEBUG] send button click', userInput); sendMessage()"
                    >
                      <q-tooltip v-if="!currentConversationId">Select or create a conversation to send a message</q-tooltip>
                    </q-btn>
                  </template>
                </q-input>
              </q-card-actions>
            </div>
          </div>
        </q-card>
      </q-dialog>
    </div>
  `,
  
  styles: [
    `
    .chat-popup {
      width: 90vw;
      max-width: 1200px;
      height: 90vh;
      max-height: 800px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    
    .chat-popup .q-card__section:first-child {
      border-radius: 0;
      border-bottom: 1px solid rgba(0,0,0,0.1);
    }
    
    .chat-popup .q-card__actions {
      padding: 12px;
      border-top: 1px solid rgba(0,0,0,0.1);
      background-color: #f5f5f5;
    }
    
    .conversation-list {
      border-right: 1px solid rgba(0,0,0,0.1);
      min-width: 200px;
      max-width: 240px;
      flex: 0 0 220px;
    }
    
    .conversation-item {
      border-radius: 4px;
      margin: 4px 8px;
    }
    
    .conversation-item--active {
      background-color: #e3f2fd;
      color: #1976d2;
    }
    
    .message-bubble {
      max-width: 80%;
      padding: 8px 12px;
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.1);
      word-break: break-word;
    }
    
    .message-header {
      display: flex;
      align-items: center;
      font-size: 0.8rem;
      margin-bottom: 4px;
      opacity: 0.9;
    }
    
    .message-content {
      white-space: pre-line;
      line-height: 1.4;
    }
    
    .empty-state {
      height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: #9e9e9e;
    }
    
    @media (max-width: 600px) {
      .conversation-list {
        min-width: 200px;
      }
      
      .message-bubble {
        max-width: 90%;
      }
    }
    `
  ]
};

// Register the component
if (window.components) {
  window.components.ChatPopup = ChatPopup;
}

// Add chatWithCrew method to the API service
if (window.apiService) {
  window.apiService.chatWithCrew = function(data) {
    return window.axios.post('/api/consult-crew/chat', data)
      .then(function(response) {
        return response;
      })
      .catch(function(error) {
        console.error('API Error in chatWithCrew:', error);
        throw error;
      });
  };
}

// Register the component with Vue
// (createApp is already declared globally in app.js)

// Create a global event bus for Vue 3
if (!window.eventBus) {
  window.eventBus = {
    _events: {},
    on(event, callback) {
      if (!this._events[event]) this._events[event] = [];
      this._events[event].push(callback);
    },
    off(event, callback) {
      if (!this._events[event]) return;
      if (callback) {
        this._events[event] = this._events[event].filter(cb => cb !== callback);
      } else {
        delete this._events[event];
      }
    },
    emit(event, ...args) {
      if (!this._events[event]) return;
      this._events[event].forEach(callback => {
        try {
          callback(...args);
        } catch (e) {
          console.error(`Error in event handler for ${event}:`, e);
        }
      });
    }
  };
}
