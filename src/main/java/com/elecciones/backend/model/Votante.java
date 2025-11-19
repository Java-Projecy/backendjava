package com.elecciones.backend.model;

import jakarta.persistence.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "votantes")
public class Votante {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(unique = true, nullable = false)
    private String dni;

    private String nombres;
    private String apellido_paterno;
    private String apellido_materno;

    private String nombre_completo; // columna generada

    private LocalDate fecha_nacimiento;
    private Integer edad;

    private String departamento;
    private String provincia;
    private String distrito;

    private String direccion;
    private String direccion_completa;

    private String ubigeo_reniec;
    private String ubigeo_sunat;

    private String telefono;
    private String email;

    private String estado;

    private LocalDateTime created_at;
    private LocalDateTime updated_at;
    public UUID getId() {
        return id;
    }
    public void setId(UUID id) {
        this.id = id;
    }
    public String getDni() {
        return dni;
    }
    public void setDni(String dni) {
        this.dni = dni;
    }
    public String getNombres() {
        return nombres;
    }
    public void setNombres(String nombres) {
        this.nombres = nombres;
    }
    public String getApellido_paterno() {
        return apellido_paterno;
    }
    public void setApellido_paterno(String apellido_paterno) {
        this.apellido_paterno = apellido_paterno;
    }
    public String getApellido_materno() {
        return apellido_materno;
    }
    public void setApellido_materno(String apellido_materno) {
        this.apellido_materno = apellido_materno;
    }
    public String getNombre_completo() {
        return nombre_completo;
    }
    public void setNombre_completo(String nombre_completo) {
        this.nombre_completo = nombre_completo;
    }
    public LocalDate getFecha_nacimiento() {
        return fecha_nacimiento;
    }
    public void setFecha_nacimiento(LocalDate fecha_nacimiento) {
        this.fecha_nacimiento = fecha_nacimiento;
    }
    public Integer getEdad() {
        return edad;
    }
    public void setEdad(Integer edad) {
        this.edad = edad;
    }
    public String getDepartamento() {
        return departamento;
    }
    public void setDepartamento(String departamento) {
        this.departamento = departamento;
    }
    public String getProvincia() {
        return provincia;
    }
    public void setProvincia(String provincia) {
        this.provincia = provincia;
    }
    public String getDistrito() {
        return distrito;
    }
    public void setDistrito(String distrito) {
        this.distrito = distrito;
    }
    public String getDireccion() {
        return direccion;
    }
    public void setDireccion(String direccion) {
        this.direccion = direccion;
    }
    public String getDireccion_completa() {
        return direccion_completa;
    }
    public void setDireccion_completa(String direccion_completa) {
        this.direccion_completa = direccion_completa;
    }
    public String getUbigeo_reniec() {
        return ubigeo_reniec;
    }
    public void setUbigeo_reniec(String ubigeo_reniec) {
        this.ubigeo_reniec = ubigeo_reniec;
    }
    public String getUbigeo_sunat() {
        return ubigeo_sunat;
    }
    public void setUbigeo_sunat(String ubigeo_sunat) {
        this.ubigeo_sunat = ubigeo_sunat;
    }
    public String getTelefono() {
        return telefono;
    }
    public void setTelefono(String telefono) {
        this.telefono = telefono;
    }
    public String getEmail() {
        return email;
    }
    public void setEmail(String email) {
        this.email = email;
    }
    public String getEstado() {
        return estado;
    }
    public void setEstado(String estado) {
        this.estado = estado;
    }
    public LocalDateTime getCreated_at() {
        return created_at;
    }
    public void setCreated_at(LocalDateTime created_at) {
        this.created_at = created_at;
    }
    public LocalDateTime getUpdated_at() {
        return updated_at;
    }
    public void setUpdated_at(LocalDateTime updated_at) {
        this.updated_at = updated_at;
    }

    // getters y setters
}
