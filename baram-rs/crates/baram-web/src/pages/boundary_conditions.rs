use leptos::*;

#[component]
pub fn BoundaryConditionsPage() -> impl IntoView {
    // In a real app, this would fetch from the API
    let (_selected_bc, set_selected_bc) = create_signal(None::<i64>);

    view! {
        <div class="page bc-page">
            <h2>"Boundary Conditions"</h2>

            <div class="bc-list">
                <div class="bc-header">
                    <span>"Name"</span>
                    <span>"Type"</span>
                </div>
                // Placeholder list
                <div class="bc-item" on:click=move |_| set_selected_bc.set(Some(1))>
                    <span>"inlet"</span>
                    <span class="bc-type-badge velocity">"Velocity Inlet"</span>
                </div>
                <div class="bc-item" on:click=move |_| set_selected_bc.set(Some(2))>
                    <span>"outlet"</span>
                    <span class="bc-type-badge pressure">"Pressure Outlet"</span>
                </div>
                <div class="bc-item" on:click=move |_| set_selected_bc.set(Some(3))>
                    <span>"walls"</span>
                    <span class="bc-type-badge wall">"Wall"</span>
                </div>
            </div>

            <div class="bc-hint">
                <p>"Click a boundary in the 3D viewport or list to edit its conditions."</p>
                <p>"Tip: Right-click a face to quick-assign a boundary type."</p>
            </div>
        </div>
    }
}
