use leptos::*;

// ════════════════════════════════════════════════════════════════
//  Root App component — main layout with navigator + viewport
// ════════════════════════════════════════════════════════════════

#[component]
pub fn App() -> impl IntoView {
    let (current_page, set_current_page) = create_signal("general".to_string());

    view! {
        <div class="baram-app">
            <header class="baram-toolbar">
                <span class="baram-logo">"BARAM"</span>
                <div class="toolbar-actions">
                    <button class="btn btn-primary" on:click=move |_| {
                        leptos::logging::log!("Save clicked");
                    }>"Save"</button>
                    <button class="btn" on:click=move |_| {
                        leptos::logging::log!("Generate case");
                    }>"Generate Case"</button>
                    <button class="btn btn-success" on:click=move |_| {
                        leptos::logging::log!("Run solver");
                    }>"Run"</button>
                </div>
            </header>

            <div class="baram-main">
                // ─── Left Navigator ──────────────────────
                <nav class="baram-navigator">
                    <div class="nav-section">
                        <h3>"Setup"</h3>
                        <NavItem label="General"           page="general"   current=current_page set_page=set_current_page />
                        <NavItem label="Models"            page="models"    current=current_page set_page=set_current_page />
                        <NavItem label="Materials"         page="materials" current=current_page set_page=set_current_page />
                        <NavItem label="Cell Zones"        page="cellzones" current=current_page set_page=set_current_page />
                        <NavItem label="Boundary Conditions" page="bcs"    current=current_page set_page=set_current_page />
                    </div>
                    <div class="nav-section">
                        <h3>"Solution"</h3>
                        <NavItem label="Numerical"         page="numerical" current=current_page set_page=set_current_page />
                        <NavItem label="Monitors"          page="monitors"  current=current_page set_page=set_current_page />
                        <NavItem label="Initialization"    page="init"      current=current_page set_page=set_current_page />
                        <NavItem label="Run Conditions"    page="run"       current=current_page set_page=set_current_page />
                    </div>
                    <div class="nav-section">
                        <h3>"Solvers"</h3>
                        <NavItem label="Solver Backends"   page="solvers"   current=current_page set_page=set_current_page />
                    </div>
                </nav>

                // ─── Center: 3D Viewport ─────────────────
                <div class="baram-viewport">
                    <canvas id="render-canvas"></canvas>
                    <div class="viewport-overlay">
                        <span class="view-label">"Isometric"</span>
                    </div>
                </div>

                // ─── Right: Properties Panel ─────────────
                <aside class="baram-properties">
                    <PageRouter page=current_page />
                </aside>
            </div>

            <footer class="baram-statusbar">
                <span>"Ready"</span>
                <span class="spacer"></span>
                <span>"Cells: 0  |  Faces: 0"</span>
            </footer>
        </div>
    }
}

#[component]
fn NavItem(
    label: &'static str,
    page: &'static str,
    current: ReadSignal<String>,
    set_page: WriteSignal<String>,
) -> impl IntoView {
    let page_owned = page.to_string();
    let is_active = move || current.get() == page;
    view! {
        <div
            class:nav-item=true
            class:active=is_active
            on:click=move |_| set_page.set(page_owned.clone())
        >
            {label}
        </div>
    }
}

#[component]
fn PageRouter(page: ReadSignal<String>) -> impl IntoView {
    view! {
        <div class="page-content">
            {move || {
                let p = page.get();
                match p.as_str() {
                    "general"   => view! { <crate::pages::general::GeneralPage /> }.into_view(),
                    "models"    => view! { <crate::pages::models::ModelsPage /> }.into_view(),
                    "bcs"       => view! { <crate::pages::boundary_conditions::BoundaryConditionsPage /> }.into_view(),
                    "numerical" => view! { <crate::pages::numerical::NumericalPage /> }.into_view(),
                    "run"       => view! { <crate::pages::run::RunPage /> }.into_view(),
                    "solvers"   => view! { <crate::pages::solvers::SolversPage /> }.into_view(),
                    _           => view! { <p>"Select a page from the navigator."</p> }.into_view(),
                }
            }}
        </div>
    }
}
