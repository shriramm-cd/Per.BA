"""
designlab_core.schemas.ui
~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic models for UI generation output.


Status: FINALISED — Literal constraint added, docstrings complete,
        json_schema_extra examples added, Field descriptions improved.

Change log (from scaffold):
- UIComponent.type restricted to Literal enum.
- model_config with json_schema_extra added to all models.
- Comprehensive docstrings and Field descriptions added throughout.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UIComponent(BaseModel): #type: ignore
    """
    A single React UI component used on one or more screens.

    UIComponents are the atomic building blocks of the interface. Each
    component has a single, clearly scoped responsibility (e.g. a password
    input field, a submit button, or an error banner). Components that are
    generic enough to appear in multiple contexts or on multiple screens
    should be marked ``reusable=True`` so that code generators can place them
    in a shared component library rather than in a screen-specific module.

    ``props`` defines the component's public API — the data and callbacks it
    receives from its parent. Every prop entry is a key-value pair where the
    key is the prop name and the value is a string describing the prop's type
    and purpose (e.g. ``"string — the user's email address"``). Props drive
    the component's behaviour and should include all inputs required for the
    component to function in isolation.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "COMP-001",
                "name": "SubmitButton",
                "type": "button",
                "description": (
                    "Primary call-to-action button that submits the login form "
                    "and displays a loading spinner while the API call is in progress."
                ),
                "props": {
                    "label": "string — button text displayed in the default state",
                    "isLoading": "boolean — shows a spinner and disables the button when true",
                    "disabled": "boolean — prevents clicks when the form is invalid",
                    "onClick": "() => void — callback invoked when the button is clicked",
                    "ariaLabel": "string — accessible label announced by screen readers",
                },
                "reusable": True,
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this component within the UIOutput. "
            "Format: COMP-NNN (zero-padded three digits), e.g. COMP-001, COMP-012. "
            "IDs are assigned sequentially starting at COMP-001 and must be "
            "referenced consistently in Screen.components lists."
        ),
    )
    name: str = Field(
        ...,
        description=(
            "PascalCase React component name matching the export name that "
            "developers will use when importing and rendering the component. "
            "Should be a clear, descriptive noun or noun phrase. "
            "Examples: 'EmailInput', 'ErrorBanner', 'UserProfileCard', 'NavBar'."
        ),
    )
    type: Literal["button", "input", "table", "modal", "card", "nav", "form", "dropdown"] = Field(
        ...,
        description=(
            "UI category of this component. Permitted values: "
            "button — clickable action triggers and icon buttons; "
            "input — text, email, password, checkbox, radio, and file fields; "
            "table — tabular data displays with rows and columns; "
            "modal — overlay dialogs, drawers, and confirmation panels; "
            "card — contained surface for grouping related content with padding and shadow; "
            "nav — navigation bars, side menus, breadcrumbs, and tab strips; "
            "form — form containers that group inputs and own submission logic; "
            "dropdown — select menus, comboboxes, and multi-select pickers."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "One sentence describing this component's single responsibility "
            "within the feature. Should be clear enough that a developer "
            "understands what to build without reading the props definition."
        ),
    )
    props: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Dictionary defining the component's public prop API. "
            "Each key is a prop name in camelCase (e.g. 'isLoading', 'onSubmit'). "
            "Each value is a string describing the prop's TypeScript type and "
            "purpose in the format 'type — description', "
            "e.g. 'boolean — disables the button when the form is submitting'. "
            "Include all props required for the component to function in isolation. "
            "An empty dict indicates the component accepts no external props."
        ),
    )
    reusable: bool = Field(
        default=False,
        description=(
            "True when this component is generic enough to be used across "
            "multiple screens or features and should be placed in a shared "
            "component library. "
            "False when the component is tightly coupled to a specific screen "
            "and should live alongside that screen's module. "
            "Examples of reusable components: buttons, input fields, modals. "
            "Examples of non-reusable components: a form that owns feature-specific "
            "submission logic, a page layout wrapper."
        ),
    )


class Screen(BaseModel): #type: ignore
    """
    A single application screen (page) rendered at a specific route.

    A Screen aggregates the UIComponents that are visible together at one
    URL. It does not embed component objects directly — instead it holds a
    list of COMP-NNN IDs that reference entries in ``UIOutput.components``.
    This separation allows the same component to appear on multiple screens
    without duplication.

    ``layout_notes`` captures the overall visual structure and responsive
    behaviour of the screen — grid columns, max-widths, alignment, and
    breakpoint rules. Responsive behaviour belongs here, not in individual
    component descriptions.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "SCR-001",
                "name": "Login Page",
                "route": "/login",
                "description": (
                    "The primary authentication screen where registered users "
                    "enter their credentials to access the application."
                ),
                "components": ["COMP-001", "COMP-002", "COMP-003", "COMP-004"],
                "layout_notes": (
                    "Single centred card on a full-height background, max-width "
                    "480px with 24px padding; vertically centred on desktop and "
                    "full-width on mobile viewports below 480px."
                ),
            }
        }
    )

    id: str = Field(
        ...,
        description=(
            "Unique identifier for this screen within the UIOutput. "
            "Format: SCR-NNN (zero-padded three digits), e.g. SCR-001. "
            "IDs are assigned sequentially starting at SCR-001."
        ),
    )
    name: str = Field(
        ...,
        description=(
            "Short, title-cased human-readable name for the screen. "
            "Should reflect the screen's purpose and match the name used "
            "in design files and the product backlog. "
            "Examples: 'Login Page', 'User Profile', 'Order History'."
        ),
    )
    route: str | None = Field(
        default=None,
        description=(
            "React Router path for this screen, starting with '/'. "
            "Use kebab-case path segments and ':param' notation for dynamic "
            "segments (e.g. '/users/:userId/profile'). "
            "Set to null only for screens that are not directly navigable "
            "(e.g. modal-only overlays rendered on top of another screen)."
        ),
    )
    description: str = Field(
        ...,
        description=(
            "One sentence describing the screen's purpose within the feature "
            "and what a user can accomplish on it."
        ),
    )
    components: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of COMP-NNN IDs for every UIComponent rendered on "
            "this screen. All referenced IDs must exist in UIOutput.components. "
            "The order should reflect the top-to-bottom, left-to-right render "
            "order on the screen. Must not be empty — a screen with no components "
            "is not a valid screen definition."
        ),
    )
    layout_notes: str | None = Field(
        default=None,
        description=(
            "One sentence describing the screen's overall layout structure and "
            "responsive behaviour across viewport sizes. Should cover grid or "
            "flex arrangement, maximum content width, alignment, and the key "
            "breakpoint at which the layout changes (e.g. stacks to single column). "
            "Responsive behaviour must be documented here rather than in individual "
            "component descriptions to avoid duplication. "
            "Set to null only when the layout is trivially obvious and requires "
            "no clarification."
        ),
    )


class UIOutput(BaseModel): #type: ignore
    """
    Root output model for the /api/generate-ui endpoint.

    Returned by generate_response() after the LLM response is parsed from JSON.
    Represents a complete, self-contained React UI definition for a single
    feature: the screens that compose the feature's user interface and the
    full catalogue of components used across those screens.

    Screens and components are stored in separate lists and linked by ID.
    ``Screen.components`` contains COMP-NNN references rather than embedded
    objects, which means a single UIComponent can be referenced by multiple
    screens without duplication. Code generators should build the component
    catalogue first, then wire screens to their component IDs.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "screens": [
                    {
                        "id": "SCR-001",
                        "name": "Login Page",
                        "route": "/login",
                        "description": "The primary authentication screen.",
                        "components": ["COMP-001", "COMP-002"],
                        "layout_notes": (
                            "Single centred card, max-width 480px on desktop, "
                            "full-width on mobile."
                        ),
                    }
                ],
                "components": [
                    {
                        "id": "COMP-001",
                        "name": "LoginForm",
                        "type": "form",
                        "description": "Owns credential state and submission logic.",
                        "props": {
                            "onSuccess": "() => void — called after successful authentication",
                        },
                        "reusable": False,
                    },
                    {
                        "id": "COMP-002",
                        "name": "SubmitButton",
                        "type": "button",
                        "description": "Submits the form and shows a loading state.",
                        "props": {
                            "isLoading": "boolean — shows spinner when true",
                            "ariaLabel": "string — screen reader label",
                        },
                        "reusable": True,
                    },
                ],
            }
        }
    )

    screens: list[Screen] = Field(
        default_factory=list,
        description=(
            "Ordered list of screens that together compose the feature's user "
            "interface. Each screen is rendered at a specific route and "
            "references its components by COMP-NNN ID. An empty list indicates "
            "the feature has no navigable screens (unusual; most features have "
            "at least one)."
        ),
    )
    components: list[UIComponent] = Field(
        default_factory=list,
        description=(
            "Complete catalogue of UIComponents used across all screens in this "
            "output. Every COMP-NNN ID referenced in any Screen.components list "
            "must have a corresponding entry here. Components marked reusable=True "
            "should be implemented in a shared library; those marked reusable=False "
            "can live alongside their owning screen's module."
        ),
    )
