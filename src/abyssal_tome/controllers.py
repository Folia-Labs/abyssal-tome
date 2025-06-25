class CardController:
    def __init__(self, card_model, card_view) -> None:
        """
        Initialize the CardController with a card model and a card view.
        """
        self.card_model = card_model
        self.card_view = card_view

    def set_card_name(self, name) -> None:
        """
        Set the name attribute of the card model to the specified value.
        
        Parameters:
            name: The new name to assign to the card model.
        """
        self.card_model.name = name

    def get_card_name(self):
        """
        Return the current name of the card from the card model.
        """
        return self.card_model.name

    def update_view(self) -> None:
        """
        Refreshes the card view to display the current state of the card model.
        """
        self.card_view.display_card(self.card_model)
