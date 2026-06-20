import Foundation
import Observation
import Security

struct AppConfiguration: Codable, Equatable {
    var mode: ConnectionMode = .localWiFi
    var localBaseURLString: String = ""
    var remoteBaseURLString: String = ""
    var readToken: String = ""

    var isReady: Bool {
        !readToken.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && (localBaseURL != nil || remoteBaseURL != nil)
    }

    var localBaseURL: URL? {
        normalizedURL(from: localBaseURLString)
    }

    var remoteBaseURL: URL? {
        normalizedURL(from: remoteBaseURLString)
    }

    private func normalizedURL(from rawValue: String) -> URL? {
        let cleaned = rawValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleaned.isEmpty, var components = URLComponents(string: cleaned) else {
            return nil
        }
        if components.scheme == nil {
            components.scheme = "http"
        }
        guard let scheme = components.scheme?.lowercased(),
              ["http", "https"].contains(scheme),
              components.host != nil else {
            return nil
        }
        return components.url
    }
}

struct GreenhouseAPIClient {
    enum APIError: LocalizedError {
        case badStatus(Int)

        var errorDescription: String? {
            switch self {
            case .badStatus(let status):
                "The server returned HTTP \(status)."
            }
        }
    }

    var session: URLSession = .shared

    func fetchLatest(baseURL: URL, token: String) async throws -> AppLatestResponse {
        let url = endpoint("api/v1/app/latest", from: baseURL)
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 8
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.badStatus(-1)
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw APIError.badStatus(httpResponse.statusCode)
        }
        return try JSONDecoder().decode(AppLatestResponse.self, from: data)
    }

    private func endpoint(_ path: String, from baseURL: URL) -> URL {
        if baseURL.path.hasSuffix(path) {
            return baseURL
        }
        return baseURL.appending(path: path)
    }
}

struct PairingCodeParser {
    enum PairingError: LocalizedError {
        case empty
        case invalid

        var errorDescription: String? {
            switch self {
            case .empty:
                "Enter or scan a pairing code."
            case .invalid:
                "That pairing code could not be read."
            }
        }
    }

    func parse(_ input: String) throws -> PairingPayload {
        let code = extractCode(from: input)
        guard !code.isEmpty else {
            throw PairingError.empty
        }

        if let jsonData = code.data(using: .utf8),
           let payload = try? JSONDecoder().decode(PairingPayload.self, from: jsonData) {
            return payload
        }

        var normalized = code
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        while normalized.count % 4 != 0 {
            normalized.append("=")
        }

        guard let data = Data(base64Encoded: normalized),
              let payload = try? JSONDecoder().decode(PairingPayload.self, from: data) else {
            throw PairingError.invalid
        }
        return payload
    }

    private func extractCode(from input: String) -> String {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let components = URLComponents(string: trimmed),
              let queryItems = components.queryItems else {
            return trimmed
        }
        return queryItems.first(where: { $0.name == "code" })?.value ?? trimmed
    }
}

struct DashboardCache {
    private let key = "greenhouse.latestPayload"
    var defaults: UserDefaults = .standard

    func load() -> AppLatestResponse? {
        guard let data = defaults.data(forKey: key) else {
            return nil
        }
        return try? JSONDecoder().decode(AppLatestResponse.self, from: data)
    }

    func save(_ payload: AppLatestResponse) {
        guard let data = try? JSONEncoder().encode(payload) else {
            return
        }
        defaults.set(data, forKey: key)
    }
}

struct KeychainTokenStore {
    private let service = "com.astrog1324.greenhousemonitor"
    private let account = "greenhouse-read-token"

    func readToken() -> String? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess,
              let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            return nil
        }
        return token
    }

    func saveToken(_ token: String) throws {
        let data = Data(token.utf8)
        var query = baseQuery()
        let update = [kSecValueData as String: data]
        let status = SecItemUpdate(query as CFDictionary, update as CFDictionary)
        if status == errSecSuccess {
            return
        }
        if status == errSecItemNotFound {
            query[kSecValueData as String] = data
            let addStatus = SecItemAdd(query as CFDictionary, nil)
            guard addStatus == errSecSuccess else {
                throw KeychainError.unhandled(addStatus)
            }
            return
        }
        throw KeychainError.unhandled(status)
    }

    private func baseQuery() -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
    }

    enum KeychainError: LocalizedError {
        case unhandled(OSStatus)

        var errorDescription: String? {
            switch self {
            case .unhandled(let status):
                "Keychain error \(status)."
            }
        }
    }
}

@MainActor
@Observable
final class DashboardStore {
    var configuration: AppConfiguration
    var payload: AppLatestResponse?
    var source: ReadingSource?
    var isLoading = false
    var errorMessage: String?

    private let configurationKey = "greenhouse.configuration"
    private let apiClient: GreenhouseAPIClient
    private let cache: DashboardCache
    private let tokenStore: KeychainTokenStore
    private let pairingParser = PairingCodeParser()
    private var isRefreshInFlight = false

    init(
        apiClient: GreenhouseAPIClient = GreenhouseAPIClient(),
        cache: DashboardCache = DashboardCache(),
        tokenStore: KeychainTokenStore = KeychainTokenStore(),
        defaults: UserDefaults = .standard
    ) {
        self.apiClient = apiClient
        self.cache = cache
        self.tokenStore = tokenStore

        if let data = defaults.data(forKey: configurationKey),
           var decoded = try? JSONDecoder().decode(AppConfiguration.self, from: data) {
            decoded.readToken = tokenStore.readToken() ?? decoded.readToken
            self.configuration = decoded
        } else {
            self.configuration = AppConfiguration(readToken: tokenStore.readToken() ?? "")
        }
    }

    var isConfigured: Bool {
        configuration.isReady
    }

    func loadCachedPayload() {
        if payload == nil {
            payload = cache.load()
        }
    }

    func applyPairingCode(_ code: String) throws {
        let pairing = try pairingParser.parse(code)
        configuration.localBaseURLString = pairing.localBaseURL
        configuration.remoteBaseURLString = pairing.remoteBaseURL ?? configuration.remoteBaseURLString
        configuration.readToken = pairing.readToken
        saveConfiguration(configuration)
    }

    func saveConfiguration(_ updated: AppConfiguration) {
        configuration = updated
        if let data = try? JSONEncoder().encode(updated) {
            UserDefaults.standard.set(data, forKey: configurationKey)
        }
        do {
            try tokenStore.saveToken(updated.readToken.trimmingCharacters(in: .whitespacesAndNewlines))
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refresh(showLoading: Bool = true) async {
        guard configuration.isReady else {
            errorMessage = "Pair with your Pi or enter connection settings."
            return
        }
        guard !isRefreshInFlight else {
            return
        }

        isRefreshInFlight = true
        if showLoading {
            isLoading = true
        }
        defer {
            isRefreshInFlight = false
            if showLoading {
                isLoading = false
            }
        }

        let token = configuration.readToken.trimmingCharacters(in: .whitespacesAndNewlines)
        let targets = requestTargets()
        var lastError: Error?

        for target in targets {
            do {
                let latest = try await apiClient.fetchLatest(baseURL: target.url, token: token)
                payload = latest
                source = target.source
                cache.save(latest)
                errorMessage = nil
                return
            } catch is CancellationError {
                return
            } catch {
                lastError = error
            }
        }

        errorMessage = lastError?.localizedDescription ?? "Could not reach the greenhouse monitor."
    }

    private func requestTargets() -> [(url: URL, source: ReadingSource)] {
        var targets: [(URL, ReadingSource)] = []
        if let localURL = configuration.localBaseURL {
            targets.append((localURL, .local))
        }
        if configuration.mode != .localWiFi, let remoteURL = configuration.remoteBaseURL {
            targets.append((remoteURL, .remote))
        }
        return targets
    }
}
