from src.database.weviate import WeaviateHelper
import os
import sys

def list_collections(weaviate_helper):
    """List all collections in Weaviate."""
    collections = weaviate_helper.list_collections()
    if collections:
        print("\nAvailable collections in Weaviate:")
        for i, collection in enumerate(collections, 1):
            print(f"{i}. {collection['name']} - {collection['description']}")
    else:
        print("No collections found in Weaviate.")


def delete_collections_except(weaviate_helper, collection_to_keep):
    """Delete all collections except the specified one."""
    print(f"\nPreparing to delete all collections except '{collection_to_keep}'...")
    
    # Get current collections
    collections = weaviate_helper.list_collections()
    collection_names = [c['name'] for c in collections]
    
    if collection_to_keep not in collection_names:
        print(f"Warning: Collection '{collection_to_keep}' does not exist. No collections will be kept.")
    
    # Ask for confirmation
    collections_to_delete = [name for name in collection_names if name != collection_to_keep]
    
    if not collections_to_delete:
        print("No collections to delete.")
        return
    
    print("\nThe following collections will be deleted:")
    for name in collections_to_delete:
        print(f"- {name}")
    
    confirm = input("\nAre you sure you want to continue? (y/n): ")
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Perform deletion
    print("\nDeleting collections...")
    result = weaviate_helper.delete_all_collections_except(collection_to_keep)
    
    # Show results
    print("\nOperation completed:")
    print(f"- Kept collection: {result['kept']}")
    if result['deleted']:
        print("- Deleted collections:")
        for name in result['deleted']:
            print(f"  - {name}")
    if result['errors']:
        print("\nErrors occurred while deleting:")
        for error in result['errors']:
            print(f"- {error['collection']}: {error['error']}")


def main():
    try:
        # Initialize the Weaviate helper
        weaviate_helper = WeaviateHelper(
            weaviate_api_key="test_apikey_**//",
            weaviate_host="127.0.0.1",
            weaviate_port="8080",
            weaviate_grpc_port="50051"
        )
        
        while True:
            print("\n=== Weaviate Collection Manager ===")
            print("1. List all collections")
            print("2. Delete all collections except 'Knowledge'")
            print("3. Exit")
            
            choice = input("\nEnter your choice (1-3): ")
            
            if choice == '1':
                list_collections(weaviate_helper)
            elif choice == '2':
                delete_collections_except(weaviate_helper, "Knowledge")
            elif choice == '3':
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please try again.")
            
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())