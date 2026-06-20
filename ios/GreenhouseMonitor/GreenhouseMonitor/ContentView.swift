import SwiftUI

enum SheetDestination: Identifiable {
    case pairing
    case settings

    var id: String { String(describing: self) }
}

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @State private var store = DashboardStore()
    @State private var sheet: SheetDestination?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if store.isConfigured {
                        dashboard
                    } else {
                        setupPrompt
                    }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Greenhouse")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        sheet = .pairing
                    } label: {
                        Label("Pair", systemImage: "qrcode.viewfinder")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        sheet = .settings
                    } label: {
                        Label("Settings", systemImage: "gear")
                    }
                }
            }
        }
        .sheet(item: $sheet) { destination in
            switch destination {
            case .pairing:
                PairingView(store: store)
            case .settings:
                SettingsView(store: store)
            }
        }
        .task {
            store.loadCachedPayload()
            while !Task.isCancelled {
                if store.isConfigured {
                    await store.refresh(showLoading: store.payload == nil)
                }
                do {
                    try await Task.sleep(for: .seconds(30))
                } catch {
                    return
                }
            }
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active, store.isConfigured else {
                return
            }
            Task {
                await store.refresh(showLoading: false)
            }
        }
        .refreshable {
            await store.refresh()
        }
    }

    @ViewBuilder
    private var dashboard: some View {
        if let current = store.payload?.current {
            HStack {
                StatusPill(isStale: current.isStale)
                Spacer()
                if let source = store.source {
                    Text(source.rawValue)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: 12)], spacing: 12) {
                MetricTile(title: "Temperature", value: formatted(current.temperatureC, suffix: "C"))
                MetricTile(title: "Humidity", value: formatted(current.humidityPct, suffix: "%"))
                MetricTile(title: "Light", value: formatted(current.lightLux, suffix: "lux"))
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Last updated")
                    .font(.headline)
                Text(current.measurementAtUTC)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                if let error = current.error, !error.isEmpty {
                    Label(error, systemImage: "exclamationmark.triangle")
                        .font(.footnote)
                        .foregroundStyle(.orange)
                }
            }
            .padding()
            .background(.background)
            .clipShape(RoundedRectangle(cornerRadius: 8))
        } else {
            ContentUnavailableView(
                "Waiting for readings",
                systemImage: "leaf",
                description: Text("The Pi is paired, but it has not returned a sensor reading yet.")
            )
        }

        if store.isLoading {
            ProgressView("Refreshing")
        }

        if let errorMessage = store.errorMessage {
            Label(errorMessage, systemImage: "exclamationmark.triangle")
                .foregroundStyle(.orange)
        }
    }

    private var setupPrompt: some View {
        VStack(alignment: .leading, spacing: 12) {
            Image(systemName: "leaf.circle")
                .font(.system(size: 48))
                .foregroundStyle(.green)
            Text("Pair your Raspberry Pi")
                .font(.title2.bold())
            Text("Open the Pi setup page, then scan the QR code or paste the manual pairing code.")
                .foregroundStyle(.secondary)
            Button {
                sheet = .pairing
            } label: {
                Label("Pair Greenhouse Monitor", systemImage: "qrcode.viewfinder")
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func formatted(_ value: Double?, suffix: String) -> String {
        guard let value else {
            return "--"
        }
        return "\(value.formatted(.number.precision(.fractionLength(0...1)))) \(suffix)"
    }
}

struct MetricTile: View {
    var title: String
    var value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.title2.bold())
                .minimumScaleFactor(0.75)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.background)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

struct StatusPill: View {
    var isStale: Bool

    var body: some View {
        Label(isStale ? "Offline or stale" : "Fresh", systemImage: isStale ? "wifi.slash" : "checkmark.circle")
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(isStale ? Color.orange.opacity(0.15) : Color.green.opacity(0.15))
            .foregroundStyle(isStale ? .orange : .green)
            .clipShape(Capsule())
    }
}

#Preview {
    ContentView()
}
