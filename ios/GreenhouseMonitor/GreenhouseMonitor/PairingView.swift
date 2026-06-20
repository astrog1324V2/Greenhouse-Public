import SwiftUI

struct PairingView: View {
    @Bindable var store: DashboardStore
    @Environment(\.dismiss) private var dismiss
    @State private var pairingCode = ""
    @State private var errorMessage: String?
    @State private var isShowingScanner = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Scan") {
                    Button {
                        isShowingScanner = true
                    } label: {
                        Label("Scan Pi QR Code", systemImage: "qrcode.viewfinder")
                    }
                }

                Section("Manual Code") {
                    TextEditor(text: $pairingCode)
                        .frame(minHeight: 140)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()

                    Button("Pair With Code") {
                        pair(using: pairingCode)
                    }
                    .disabled(pairingCode.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }

                if let errorMessage {
                    Section {
                        Label(errorMessage, systemImage: "exclamationmark.triangle")
                            .foregroundStyle(.orange)
                    }
                }
            }
            .navigationTitle("Pair Pi")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
        .sheet(isPresented: $isShowingScanner) {
            QRScannerView { code in
                isShowingScanner = false
                pair(using: code)
            }
        }
    }

    private func pair(using code: String) {
        do {
            try store.applyPairingCode(code)
            Task {
                await store.refresh()
            }
            dismiss()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

