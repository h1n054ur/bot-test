import os
import sys
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict, Tuple

class BaseMenu(ABC):
    """Base class for all menus in the CLI application.
    
    Provides common functionality for rendering headers, clearing the screen,
    and handling user input prompts.
    """
    
    def __init__(self, title: str):
        """Initialize a new menu with the given title.
        
        Args:
            title: The title to display at the top of the menu
        """
        self.title = title
    
    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def render_header(self) -> None:
        """Render the menu header with the title."""
        self.clear_screen()
        print("=" * 60)
        print(f"{self.title.center(60)}")
        print("=" * 60)
        print()
    
    def prompt_for_input(self, message: str, default: Optional[str] = None) -> str:
        """Prompt the user for input with an optional default value.
        
        Args:
            message: The message to display to the user
            default: Optional default value if user enters nothing
            
        Returns:
            The user's input or the default value
        """
        if default:
            user_input = input(f"{message} [{default}]: ").strip()
            return user_input if user_input else default
        else:
            return input(f"{message}: ").strip()
    
    def prompt_for_choice(self, message: str, options: List[str], 
                         allow_back: bool = True) -> int:
        """Prompt the user to choose from a list of options.
        
        Args:
            message: The message to display to the user
            options: List of options to display
            allow_back: Whether to allow a 'back' option
            
        Returns:
            The index of the selected option (0-based)
        """
        print(f"{message}:")
        
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        if allow_back:
            print(f"0. Back")
        
        while True:
            try:
                choice = int(input("\nEnter your choice: "))
                if allow_back and choice == 0:
                    return -1  # Special code for 'back'
                if 1 <= choice <= len(options):
                    return choice - 1  # Convert to 0-based index
                print(f"Please enter a number between {'0' if allow_back else '1'} and {len(options)}")
            except ValueError:
                print("Please enter a valid number")
    
    def prompt_for_confirmation(self, message: str) -> bool:
        """Prompt the user for a yes/no confirmation.
        
        Args:
            message: The confirmation message to display
            
        Returns:
            True if the user confirms, False otherwise
        """
        response = input(f"{message} (y/n): ").strip().lower()
        return response in ('y', 'yes')
    
    def display_error(self, message: str) -> None:
        """Display an error message to the user.
        
        Args:
            message: The error message to display
        """
        print(f"\nERROR: {message}")
        input("\nPress Enter to continue...")
    
    def display_success(self, message: str) -> None:
        """Display a success message to the user.
        
        Args:
            message: The success message to display
        """
        print(f"\nSUCCESS: {message}")
        input("\nPress Enter to continue...")
    
    def render_table(self, headers: List[str], rows: List[List[Any]], 
                    title: Optional[str] = None) -> None:
        """Render a simple ASCII table with the given headers and rows.
        
        Args:
            headers: List of column headers
            rows: List of rows, where each row is a list of values
            title: Optional title for the table
        """
        if not rows:
            print("No data to display.")
            return
        
        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Add padding
        col_widths = [w + 2 for w in col_widths]
        
        # Calculate total width
        total_width = sum(col_widths) + len(headers) - 1
        
        # Print title if provided
        if title:
            print(f"\n{title}")
            print("-" * total_width)
        
        # Print headers
        header_row = ""
        for i, header in enumerate(headers):
            header_row += f"{header.ljust(col_widths[i])}"
            if i < len(headers) - 1:
                header_row += "|"
        print(header_row)
        print("-" * total_width)
        
        # Print rows
        for row in rows:
            row_str = ""
            for i, cell in enumerate(row):
                row_str += f"{str(cell).ljust(col_widths[i])}"
                if i < len(row) - 1:
                    row_str += "|"
            print(row_str)
    
    @abstractmethod
    def display(self) -> Any:
        """Display the menu and handle user interaction.
        
        This method must be implemented by all subclasses.
        
        Returns:
            The result of the menu interaction, which could be the next menu to display,
            a value to return to the parent menu, or None to exit.
        """
        pass