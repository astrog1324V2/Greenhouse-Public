import SwiftUI

struct SettingsView: View {
    @Bindable var store: DashboardStore
    @Environment(\.dismiss) private var dismiss
    @State private var configuration: AppConfiguration

    init(store: DashboardStore) {
        self.store = store
        _configuration = State(initialValue: store.configuration)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Connection Mode") {
                    Picker("Mode", selection: $configuration.mode) {
                        ForEach(ConnectionMode.allCases) { mode in
                            Text(mode.title).tag(mode)
                        }
                    }
                }

                Section("Local Pi") {
                    TextField("http://greenhouse.local:8000", text: $configuration.localBaseURLString)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                }

                Section("Remote API") {
                    TextField("https://api.example.com", text: $configuration.remoteBaseURLString)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                    Text("Self-hosted and subscription APIs are planned. Local Wi-Fi works now.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                Section("Read Token") {
                    SecureField("Read token", text: $configuration.readToken)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }

                if let errorMessage = store.errorMessage {
                    Section {
                        Label(errorMessage, systemImage: "exclamationmark.triangle")
                            .foregroundStyle(.orange)
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        store.saveConfiguration(configuration)
                        Task {
                            await store.refresh()
                        }
                        dismiss()
                    }
                }
            }
        }
    }
}

