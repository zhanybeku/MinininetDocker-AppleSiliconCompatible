#!/bin/sh

add_user() {
    echo "add_user function - not implemented yet"
    return 0
}

list_users() {
    if [ -f "users.json" ]; then
        cat users.json
    else
        echo "users.json file not found"
        return 1
    fi
}

# Interactive menu function
interactive_menu() {
    while true; do
        echo ""
        echo "=== User Management System ==="
        echo "1. List users"
        echo "2. Add user"
        echo "3. Exit"
        echo ""
        read -p "Choose an option (1-3): " choice
        
        case $choice in
            1)
                list_users
                ;;
            2)
                add_user
                ;;
            3)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo "Invalid option. Please choose 1, 2, or 3."
                ;;
        esac
    done
}

# Main section - only run if script is executed directly (not sourced)
if [ "$0" = "app-run.sh" ] || [ "$0" = "./app-run.sh" ]; then
    case "$1" in
        "add_user")
            add_user "$2" "$3"  # Pass additional arguments if needed
            ;;
        "list_users")
            list_users
            ;;
        "interactive"|"menu")
            interactive_menu
            ;;
        "")
            interactive_menu  # Default to interactive mode if no arguments
            ;;
        *)
            echo "Usage: $0 {add_user|list_users|interactive|menu}"
            echo "Examples:"
            echo "  $0 list_users"
            echo "  $0 add_user"
            echo "  $0 interactive  # or just $0"
            echo ""
            echo "To use functions directly:"
            echo "  source app-run.sh"
            echo "  list_users"
            echo "  add_user"
            exit 1
            ;;
    esac
fi
