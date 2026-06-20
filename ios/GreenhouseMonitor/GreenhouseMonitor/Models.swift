import Foundation

struct AppLatestResponse: Codable, Equatable {
    var generatedAtUTC: String
    var deviceID: String
    var deviceName: String
    var current: SensorSnapshot?

    enum CodingKeys: String, CodingKey {
        case generatedAtUTC = "generated_at_utc"
        case deviceID = "device_id"
        case deviceName = "device_name"
        case current
    }
}

struct HistoryResponse: Codable, Equatable {
    var generatedAtUTC: String
    var deviceID: String
    var hours: Int
    var readings: [SensorSnapshot]

    enum CodingKeys: String, CodingKey {
        case generatedAtUTC = "generated_at_utc"
        case deviceID = "device_id"
        case hours
        case readings
    }
}

struct SensorSnapshot: Codable, Equatable {
    var temperatureC: Double?
    var humidityPct: Double?
    var lightLux: Double?
    var measurementAtUTC: String
    var ageSeconds: Int
    var isStale: Bool
    var error: String?

    enum CodingKeys: String, CodingKey {
        case temperatureC = "temperature_c"
        case humidityPct = "humidity_pct"
        case lightLux = "light_lux"
        case measurementAtUTC = "measurement_at_utc"
        case ageSeconds = "age_seconds"
        case isStale = "is_stale"
        case error
    }
}

struct PairingPayload: Codable, Equatable {
    var version: Int
    var name: String
    var deviceID: String
    var localBaseURL: String
    var remoteBaseURL: String?
    var readToken: String

    enum CodingKeys: String, CodingKey {
        case version
        case name
        case deviceID = "device_id"
        case localBaseURL = "local_base_url"
        case remoteBaseURL = "remote_base_url"
        case readToken = "read_token"
    }
}

enum ConnectionMode: String, CaseIterable, Codable, Identifiable {
    case localWiFi
    case selfHostedAPI
    case subscriptionAPI

    var id: String { rawValue }

    var title: String {
        switch self {
        case .localWiFi:
            "Local Wi-Fi"
        case .selfHostedAPI:
            "Self-hosted API"
        case .subscriptionAPI:
            "Subscription API"
        }
    }
}

enum ReadingSource: String {
    case local = "Local Wi-Fi"
    case remote = "Remote API"
}

