import itertools as it

# --- Core Sudoku Definitions ---
DOM = set(range(1, 10))
ID_COLS = "ABCDEFGHI"
# Generates cell keys like A1, B1, ..., I1, A2, B2, ..., I9
# This order must match the input file format if it's one value per line.
# Original strKeys generation:
# keys_orig = list(it.product(range(1,10),ID_COLS)) # (1,'A'), (1,'B')...
# STR_KEYS = [f"{key[1]}{key[0]}" for key in keys_orig] # A1, B1...I1, A2, B2...I2 etc.

# Standard cell key generation (A1, A2, ... A9, B1, ... B9)
# This is often more common for 81-char string or line-by-line inputs
# where file is A1 val, A2 val, ... A9 val, B1 val ...
# For consistency with the provided snippet's likely file reading loop,
# we'll stick to its strKeys generation. If your file is A1..A9, B1..B9, etc.,
# then STR_KEYS should be: [f"{col}{row}" for col in ID_COLS for row in range(1, 10)]
# We will assume the file format matches the user's original strKeys implied order:
# Line 1: A1, Line 2: B1, ..., Line 9: I1, Line 10: A2, etc.
_keys_for_strKeys = list(it.product(range(1,10), ID_COLS)) # (1,'A'), (1,'B'),...,(1,'I'),(2,'A')...
STR_KEYS = [f"{col_char}{row_num}" for row_num, col_char in _keys_for_strKeys] # A1,B1,...,I1,A2,B2,...,I2...


# --- Constraint Definitions (from user's code, with minor adjustments) ---
def define_column_constraints(id_cols, domain_values):
    col_constraints = []
    for col_id in id_cols:
        constraint_vars = [f"{col_id}{i}" for i in domain_values]
        col_constraints.append(constraint_vars)
    return col_constraints

def define_row_constraints(id_cols, domain_values):
    row_constraints = []
    for i in domain_values: # For each row number
        # Corrected to form keys like A1, B1, C1 for row 1
        constraint_vars = [f"{col_id}{i}" for col_id in id_cols]
        row_constraints.append(constraint_vars)
    return row_constraints

def define_box_constraints(id_cols_str, domain_values):
    all_boxes = []
    id_cols_list = list(id_cols_str)
    for row_start in range(1, 10, 3): # 1, 4, 7
        for col_idx_start in range(0, 9, 3): # 0, 3, 6 (indices for id_cols_list)
            vars_box = []
            for i in range(3): # Offset in row for the box
                for j in range(3): # Offset in col for the box
                    row = row_start + i
                    col_char = id_cols_list[col_idx_start + j]
                    vars_box.append(f"{col_char}{row}")
            all_boxes.append(vars_box)
    return all_boxes

ALL_CONSTRAINTS = (define_column_constraints(ID_COLS, DOM) +
                   define_row_constraints(ID_COLS, DOM) +
                   define_box_constraints(ID_COLS, DOM))

# --- CSP Solver Functions ---

def is_assignment_complete(assignment, all_vars):
    """Checks if all variables have been assigned."""
    return len(assignment) == len(all_vars)

def select_unassigned_variable_mrv(assignment, domains, all_vars):
    """Selects the unassigned variable with the Minimum Remaining Values (MRV)."""
    unassigned_vars = [v for v in all_vars if v not in assignment]
    if not unassigned_vars:
        return None

    mrv_var = None
    min_domain_size = float('inf')

    for var in unassigned_vars:
        if var not in domains: # Should not happen with proper initialization
            print(f"Warning: Variable {var} not in domains during MRV selection.")
            continue
        current_domain_size = len(domains[var])
        if current_domain_size < min_domain_size:
            min_domain_size = current_domain_size
            mrv_var = var
        # Tie-breaking (e.g., degree heuristic) could be added here for further optimization.
    return mrv_var

def order_domain_values(variable, domains):
    """Orders the values in the domain of the variable. Simple numerical sort for now."""
    if variable not in domains:
        print(f"Warning: Variable {variable} not found in domains for value ordering.")
        return []
    return sorted(list(domains[variable]))

def is_consistent_with_assignment(variable, value, assignment, constraints):
    """
    Checks if assigning 'value' to 'variable' is consistent with current 'assignment'
    based on the Sudoku rules (constraints).
    """
    for constraint_group in constraints:
        if variable in constraint_group:
            for peer_var in constraint_group:
                if peer_var != variable and peer_var in assignment:
                    if assignment[peer_var] == value:
                        return False
    return True

def forward_check(assigned_var, assigned_value, assignment, current_domains, domain_changes_log, constraints):
    """
    Performs forward checking after assigning 'assigned_value' to 'assigned_var'.
    Updates 'current_domains' and logs changes in 'domain_changes_log'.
    Returns True if successful, False if an inconsistency (empty domain) is found.
    'assignment' here should ALREADY contain the new assignment of assigned_var.
    """
    for constraint_group in constraints:
        if assigned_var in constraint_group:
            for neighbor in constraint_group:
                # Consider only unassigned neighbors
                if neighbor != assigned_var and neighbor not in assignment: # neighbor is not yet assigned
                    if assigned_value in current_domains[neighbor]:
                        current_domains[neighbor].discard(assigned_value)
                        domain_changes_log.append((neighbor, assigned_value)) # Log for potential undo
                        if not current_domains[neighbor]: # Domain becomes empty
                            return False # Inconsistency found
    return True

def backtrack_solve(assignment, current_domains):
    """
    Recursive backtracking function to solve the Sudoku.
    'current_domains' is modified by this function and its children;
    changes are reverted upon backtracking.
    """
    if is_assignment_complete(assignment, STR_KEYS):
        return assignment # Solution found

    variable_to_assign = select_unassigned_variable_mrv(assignment, current_domains, STR_KEYS)
    if variable_to_assign is None: # Should only happen if MRV has an issue or logic error
        print("Error: No variable selected by MRV, but assignment not complete.")
        return None

    for value in order_domain_values(variable_to_assign, current_domains):
        if is_consistent_with_assignment(variable_to_assign, value, assignment, ALL_CONSTRAINTS):
            assignment[variable_to_assign] = value
            domain_changes_fc = [] # Log for values removed by forward checking

            # Perform Forward Checking
            if forward_check(variable_to_assign, value, assignment, current_domains, domain_changes_fc, ALL_CONSTRAINTS):
                result = backtrack_solve(assignment, current_domains)
                if result:
                    return result # Solution found and propagated

            # Backtrack: Undo assignment and Forward Checking changes
            # Undo FC changes first
            for var_changed, val_removed in domain_changes_fc:
                current_domains[var_changed].add(val_removed)
            # Undo assignment
            del assignment[variable_to_assign]

    return None # No solution found from this path

def apply_initial_consistency(domains, constraints):
    """
    Applies a basic consistency check (arc consistency for unary constraints).
    Repeatedly removes values from domains if a variable in a constraint is uniquely assigned.
    Modifies 'domains' in place. Returns True if consistent, False if any domain becomes empty.
    """
    changed_in_iteration = True
    while changed_in_iteration:
        changed_in_iteration = False
        for constraint_group in constraints:
            for var1 in constraint_group:
                if len(domains[var1]) == 1: # var1 is assigned
                    val_to_remove = list(domains[var1])[0]
                    for var2 in constraint_group:
                        if var1 != var2 and val_to_remove in domains[var2]:
                            domains[var2].discard(val_to_remove)
                            changed_in_iteration = True
                            if not domains[var2]: # Domain wiped out
                                print(f"Inconsistency found during initial propagation: {var2} domain empty.")
                                return False
    return True

def solve_sudoku_from_file(board_filepath):
    """
    Main function to load a Sudoku from a file and solve it.
    """
    initial_domains = {key: DOM.copy() for key in STR_KEYS}

    try:
        with open(board_filepath, 'r') as f:
            # Assumes file has 81 lines, one for each cell.
            # Order of lines must match STR_KEYS: A1, B1, C1...I1, A2, B2...I2 etc.
            # '0' or any non-digit (1-9) character represents an empty cell.
            for key in STR_KEYS:
                line_val = f.readline().strip()
                if line_val and line_val.isdigit() and line_val != '0':
                    val_num = int(line_val)
                    if 1 <= val_num <= 9:
                        initial_domains[key] = {val_num}
                    else:
                        print(f"Warning: Invalid number '{line_val}' for {key} in input. Treating as empty.")
                # If line_val is '0', non-digit, or empty, it's an empty cell; domain remains full.
            # Check if enough lines were read
            if f.readline(): # If there's still data, file might be too long
                print("Warning: File may contain more than 81 lines of relevant data.")

    except FileNotFoundError:
        print(f"Error: File '{board_filepath}' not found.")
        return None
    except Exception as e:
        print(f"Error reading or processing file '{board_filepath}': {e}")
        return None

    # Apply initial consistency propagation
    if not apply_initial_consistency(initial_domains, ALL_CONSTRAINTS):
        print("Sudoku is inconsistent after initial propagation based on input values.")
        return None

    # Start the backtracking search
    print(f"\nAttempting to solve Sudoku from: {board_filepath}")
    solution_assignment = backtrack_solve({}, initial_domains) # Start with empty assignment

    if solution_assignment:
        print("\nSolution found!")
        return solution_assignment
    else:
        print("\nNo solution found for the Sudoku.")
        return None

def print_sudoku_solution(solution_assignment):
    """Prints the Sudoku grid from a solution assignment."""
    if not solution_assignment:
        print("No solution to print.")
        return

    print("\nSolved Sudoku Grid:")
    # Standard Sudoku display: Rows 1-9, Columns A-I
    for r_num in range(1, 10): # For each row number 1..9
        if r_num > 1 and (r_num - 1) % 3 == 0:
            print("------+-------+------") # Horizontal separator for 3x3 boxes
        
        row_values = []
        for c_idx, col_char in enumerate(ID_COLS): # For each column char A..I
            key = f"{col_char}{r_num}" # Cell name e.g., A1, B1 for r_num=1
            value = solution_assignment.get(key, ".") # Get value, default to .
            row_values.append(str(value))
            if (c_idx + 1) % 3 == 0 and c_idx < len(ID_COLS) - 1:
                row_values.append("|") # Vertical separator for 3x3 boxes
        print(" ".join(row_values))

# --- Main Execution ---
if __name__ == "__main__":
    # IMPORTANT: Create a file named "sudoku_to_solve.txt" in the same directory,
    # or change the path below.
    # The file should have 81 lines. Each line is a digit for a cell.
    # '0' means empty. The order of cells in the file should be:
    # Value for A1
    # Value for B1
    # ...
    # Value for I1 (9th line)
    # Value for A2 (10th line)
    # Value for B2
    # ...
    # Value for I9 (81st line)
    
    # Example: to create a very simple Sudoku file for testing "sudoku_to_solve.txt":
    # A1=1, all others 0.
    # File content would be:
    # 1
    # 0
    # ... (79 more lines of '0')
    
    # For a Sudokumania "impossible" level, copy its representation into this format.
    # If Sudokumania gives an 81-character string (e.g. 0030206009003050010018064...),
    # you'll need a small script to convert that string into an 81-line file where
    # the character for A1 is on line 1, B1 on line 2, ..., I1 on line 9, A2 on line 10, etc.
    # OR, adjust the file reading logic in `solve_sudoku_from_file` if your input
    # format is different (e.g., an 81-character string directly).

    file_path = "sudoku_to_solve.txt" 
    print(f"Attempting to use STR_KEYS order: {STR_KEYS[:12]}...") # Print first few keys to confirm order
    
    # Create a dummy "sudoku_to_solve.txt" if it doesn't exist for quick testing
    import os
    if not os.path.exists(file_path):
        print(f"'{file_path}' not found. Creating a sample empty Sudoku file.")
        with open(file_path, 'w') as f:
            for _ in range(81):
                f.write("0\n")
        print(f"Sample '{file_path}' created with an empty Sudoku. Please replace it with your target Sudoku.")


    solved_sudoku = solve_sudoku_from_file(file_path)

    if solved_sudoku:
        print_sudoku_solution(solved_sudoku)