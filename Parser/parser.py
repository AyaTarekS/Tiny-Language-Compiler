import uuid
import sys
import json

# Increase recursion limit to handle deep syntax trees
sys.setrecursionlimit(2000)

class ASTNode:
    """
    Represents a node in the Abstract Syntax Tree (AST).
    
    Attributes:
        id (str): Unique identifier for GUI linking.
        node_type (str): The type of the node (e.g., 'if', 'assign', 'op').
        value (str): The specific value of the node (e.g., 'x', '+', '1').
        children (list): List of child ASTNodes (vertical connections).
        sibling (ASTNode): The next statement in the sequence (horizontal connection).
        shape (str): Hint for GUI rendering ('rect' for statements, 'oval' for expressions).
        depth (int): Hint for GUI layout positioning (Y-axis).
    """
    def __init__(self, node_type, value=None, shape="oval", depth=0):
        self.id = str(uuid.uuid4())
        self.node_type = node_type
        self.value = value
        self.children = []
        self.sibling = None  # Horizontal link to the next statement
        self.shape = shape
        self.depth = depth

    def add_child(self, child_node):
        """Appends a node to the children list."""
        if child_node:
            self.children.append(child_node)

    def to_dict(self):
        """
        Returns a recursive dictionary representation of the node.
        Useful for serialization and debugging.
        """
        return {
            "id": self.id,
            "type": self.node_type,
            "value": self.value,
            "shape": self.shape,
            "depth": self.depth,
            "children": [child.to_dict() for child in self.children],
            "sibling": self.sibling.to_dict() if self.sibling else None
        }

class Parser:
    """
    Recursive Descent Parser for the TINY language.
    """
    def __init__(self, tokens):
        """
        Initialize the parser with a list of tokens.

        Args:
            tokens (list): A list of tuples in the format (token_value, token_type).
        """
        self.tokens = tokens
        self.current_idx = 0
        self.errors = []
        self.token_count = len(tokens)

    def get_token(self):
        """
        Retrieves the current token without consuming it.
        
        Returns:
            tuple: (token_value, token_type) or None if EOF.
        """
        if self.current_idx < self.token_count:
            return self.tokens[self.current_idx]
        return None

    def match(self, expected_type):
        """
        Consumes the current token if it matches the expected type.

        Args:
            expected_type (str): The token type to match (e.g., 'IF', 'IDENTIFIER').

        Returns:
            str: The token value if matched.
            None: If the match fails (records an error).
        """
        token = self.get_token()
        if token and token[1] == expected_type:
            self.current_idx += 1
            return token[0]
        else:
            actual = token[1] if token else "EOF"
            self.errors.append(f"Syntax Error: Expected {expected_type}, found {actual} at index {self.current_idx}")
            return None

    def parse(self):
        """
        Executes the parsing process.

        Returns:
            dict: Contains 'status' (Accepted/Rejected), 'root' (ASTNode), and 'errors' (list).
        """
        root = self.program(depth=0)
        
        # specific check for unconsumed tokens at the end of parsing
        if self.current_idx < self.token_count and not self.errors:
            self.errors.append("Syntax Error: Unexpected tokens remaining after parsing.")
        
        status = "Accepted" if not self.errors else "Rejected"
        return {
            "status": status,
            "root": root,
            "errors": self.errors
        }

    # ------------------------------------------------------------------
    # Grammar Rules (Recursive Descent Implementation)
    # ------------------------------------------------------------------

    def program(self, depth):
        """program -> stmt-sequence"""
        return self.stmt_sequence(depth)

    def stmt_sequence(self, depth):
        """
        stmt-sequence -> statement { ; statement }
        
        Constructs a linear sequence of statements linked via the 'sibling' attribute.
        """
        first_stmt = self.statement(depth)
        current_stmt = first_stmt
        
        while True:
            token = self.get_token()
            if token and token[1] == 'SEMICOLON':
                self.match('SEMICOLON')
                next_stmt = self.statement(depth)
                if current_stmt and next_stmt:
                    current_stmt.sibling = next_stmt 
                    current_stmt = next_stmt
            else:
                break
        
        return first_stmt

    def statement(self, depth):
        """
        statement -> if-stmt | repeat-stmt | assign-stmt | read-stmt | write-stmt
        """
        token = self.get_token()
        if not token:
            return None
        
        if token[1] == 'IF':
            return self.if_stmt(depth)
        elif token[1] == 'REPEAT':
            return self.repeat_stmt(depth)
        elif token[1] == 'IDENTIFIER':
            return self.assign_stmt(depth)
        elif token[1] == 'READ':
            return self.read_stmt(depth)
        elif token[1] == 'WRITE':
            return self.write_stmt(depth)
        else:
            self.errors.append(f"Syntax Error: Unexpected token {token[0]} at start of statement.")
            self.match(token[1]) # Panic mode: consume token to avoid infinite loop
            return None

    def if_stmt(self, depth):
        """
        if-stmt -> if exp then stmt-sequence [else stmt-sequence] end
        """
        self.match('IF')
        node = ASTNode("if", shape="rect", depth=depth)
        
        # Expression part
        exp_node = self.exp(depth + 1)
        node.add_child(exp_node) 
        
        self.match('THEN')
        
        # 'Then' part statements
        then_stmts = self.stmt_sequence(depth + 1)
        node.add_child(then_stmts)
        
        # Optional 'Else' part
        token = self.get_token()
        if token and token[1] == 'ELSE':
            self.match('ELSE')
            else_stmts = self.stmt_sequence(depth + 1)
            node.add_child(else_stmts)
            
        self.match('END')
        return node

    def repeat_stmt(self, depth):
        """
        repeat-stmt -> repeat stmt-sequence until exp
        """
        self.match('REPEAT')
        node = ASTNode("repeat", shape="rect", depth=depth)
        
        body = self.stmt_sequence(depth + 1)
        node.add_child(body)
        
        self.match('UNTIL')
        test = self.exp(depth + 1)
        node.add_child(test)
        
        return node

    def assign_stmt(self, depth):
        """
        assign-stmt -> identifier := exp
        """
        name = self.match('IDENTIFIER')
        self.match('ASSIGN')
        
        # Per project slides, the variable name is part of the assign node's value
        node = ASTNode("assign", value=f"({name})", shape="rect", depth=depth)
        
        expr = self.exp(depth + 1)
        node.add_child(expr)
        
        return node

    def read_stmt(self, depth):
        """
        read-stmt -> read identifier
        """
        self.match('READ')
        name = self.match('IDENTIFIER')
        return ASTNode("read", value=f"({name})", shape="rect", depth=depth)

    def write_stmt(self, depth):
        """
        write-stmt -> write exp
        """
        self.match('WRITE')
        node = ASTNode("write", shape="rect", depth=depth)
        expr = self.exp(depth + 1)
        node.add_child(expr)
        return node

    def exp(self, depth):
        """
        exp -> simple-exp [ comparison-op simple-exp ]
        """
        lhs = self.simple_exp(depth)
        
        token = self.get_token()
        if token and token[1] in ['LESSTHAN', 'EQUAL']:
            op_str = self.match(token[1])
            # Normalize op string if necessary
            op_val = "<" if op_str == "LESSTHAN" else ("=" if op_str == "EQUAL" else op_str)
            
            # The comparison operator becomes the parent of the LHS and RHS
            op_node = ASTNode("op", value=f"({op_str})", shape="oval", depth=depth)
            op_node.add_child(lhs)
            
            rhs = self.simple_exp(depth + 1)
            op_node.add_child(rhs)
            return op_node
            
        return lhs

    def simple_exp(self, depth):
        """
        simple-exp -> term { addop term }
        Handles left-associative addition and subtraction.
        """
        lhs = self.term(depth)
        
        while True:
            token = self.get_token()
            if token and token[1] in ['PLUS', 'MINUS']:
                op_str = self.match(token[1])
                
                op_node = ASTNode("op", value=f"({op_str})", shape="oval", depth=depth)
                op_node.add_child(lhs)
                
                rhs = self.term(depth + 1)
                op_node.add_child(rhs)
                
                lhs = op_node 
            else:
                break
        return lhs

    def term(self, depth):
        """
        term -> factor { mulop factor }
        Handles left-associative multiplication and division.
        """
        lhs = self.factor(depth)
        
        while True:
            token = self.get_token()
            if token and token[1] in ['MULT', 'DIV']:
                op_str = self.match(token[1])
                
                op_node = ASTNode("op", value=f"({op_str})", shape="oval", depth=depth)
                op_node.add_child(lhs)
                
                rhs = self.factor(depth + 1)
                op_node.add_child(rhs)
                
                lhs = op_node
            else:
                break
        return lhs

    def factor(self, depth):
        """
        factor -> ( exp ) | number | identifier
        """
        token = self.get_token()
        if not token:
            return None
        
        if token[1] == 'OPENBRACKET':
            self.match('OPENBRACKET')
            node = self.exp(depth)
            self.match('CLOSEDBRACKET')
            return node
        elif token[1] == 'NUMBER':
            val = self.match('NUMBER')
            return ASTNode("const", value=f"({val})", shape="oval", depth=depth)
        elif token[1] == 'IDENTIFIER':
            val = self.match('IDENTIFIER')
            return ASTNode("id", value=f"({val})", shape="oval", depth=depth)
        else:
            self.errors.append(f"Syntax Error: Unexpected token {token[0]} in expression at index {self.current_idx}")
            self.current_idx += 1 
            return None

# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------

def load_tokens_from_file(file_path):
    """
    Parses a text file containing tokens.
    
    Expected File Format: "TokenValue, TokenType" per line.
    
    Args:
        file_path (str): Path to the input file.
        
    Returns:
        list: A list of tuples (token_value, token_type).
    """
    tokens = []
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # Split on comma, taking the last element as Type to handle commas in values
                parts = line.split(',')
                if len(parts) >= 2:
                    token_type = parts[-1].strip()
                    token_val = ",".join(parts[:-1]).strip()
                    tokens.append((token_val, token_type))
    except Exception as e:
        print(f"Error loading file: {e}")
        return []
    return tokens

def run_parser(file_path):
    """
    High-level entry point to run the parser on a file.
    
    Args:
        file_path (str): Path to the tokens file.
        
    Returns:
        dict: The parse result dictionary.
    """
    tokens = load_tokens_from_file(file_path)
    if not tokens:
        return {"status": "Error", "root": None, "errors": ["Failed to load tokens or empty file."]}
        
    parser = Parser(tokens)
    result = parser.parse()
    
    return result

def print_tree_as_json(parse_result):
    """
    Prints the parse result as a formatted JSON string.
    Handles converting ASTNode objects to dicts automatically.
    """
    # Create a copy or a new dict to avoid modifying the original if needed
    output = {
        "status": parse_result["status"],
        "root": None,
        "errors": parse_result["errors"]
    }

    # Convert root to dict if it exists (even in Rejected status, we might have a partial tree)
    root_node = parse_result.get("root")
    if root_node and hasattr(root_node, 'to_dict'):
        output["root"] = root_node.to_dict()
    
    # Now it is safe to dump because 'root' is a pure dictionary
    print(json.dumps(output, indent=4))

def save_tree_to_json(parse_result, output_file_path):
    """
    Saves the parse result to a JSON file.
    """
    output = {
        "status": parse_result["status"],
        "root": None,
        "errors": parse_result["errors"]
    }

    # Convert root to dict if it exists
    root_node = parse_result.get("root")
    if root_node and hasattr(root_node, 'to_dict'):
        output["root"] = root_node.to_dict()

    try:
        with open(output_file_path, 'w') as f:
            json.dump(output, f, indent=4)
        print(f"Successfully saved output to {output_file_path}")
    except IOError as e:
        print(f"Error writing to file {output_file_path}: {e}")

# ------------------------------------------------------------------
# Sample Usage
# ------------------------------------------------------------------
if __name__ == "__main__":
    # Create a dummy file for testing purposes
    sample_file = "input_samples//pathological.txt"
    
    print(f"Running parser on {sample_file}...")
    result = run_parser(sample_file)
    print_tree_as_json(result)
    save_tree_to_json(result, "result.json")