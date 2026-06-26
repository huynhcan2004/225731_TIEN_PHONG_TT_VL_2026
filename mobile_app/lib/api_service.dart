import 'dart:convert';
import 'package:http/http.dart' as http;
import 'config.dart';

class ApiService {
  // Lấy baseUrl từ file config.dart để dễ đồng bộ
  final String baseUrl = AppConfig.apiBaseUrl; 

  Future<Map<String, dynamic>> sendQuery(String message, String token) async {
    final response = await http.post(
      Uri.parse('$baseUrl/chatbot/query'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'message': message,
        'model': 'gemini' // Hoặc model huynh đang dùng
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body); // Trả về JSON chứa answer, graph_data...
    } else {
      throw Exception('Lỗi kết nối Backend: ${response.statusCode}');
    }
  }
}